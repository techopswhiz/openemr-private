#!/usr/bin/env bash
# Step 5: Seed OpenEMR with synthetic patient data
#
# Spins up a throwaway dev container (which has Synthea + devtools) on the
# same Docker network/volumes as production, imports ~200 random patients,
# creates 5 hospital facilities, and distributes patients across them.
#
# Usage: ./deploy-5-seed.sh [patient-count]
#   patient-count defaults to 200
#   Connects via SSH alias "openemr" (configured in ~/.ssh/config)
set -euo pipefail

PATIENT_COUNT="${1:-200}"
SSH="ssh openemr"

PROJECT="production"
NETWORK="${PROJECT}_default"
SITE_VOLUME="${PROJECT}_sitevolume"
MYSQL="docker exec ${PROJECT}-mysql-1 mariadb -u openemr -popenemr openemr"

echo "==> Seeding OpenEMR with ${PATIENT_COUNT} synthetic patients..."

# ---------------------------------------------------------------------------
# 1. Run a throwaway dev container with devtools/Synthea on the prod network
# ---------------------------------------------------------------------------
echo "==> Starting throwaway dev container (openemr/openemr:flex)..."
$SSH "docker pull openemr/openemr:flex"
$SSH "docker rm -f openemr-seed 2>/dev/null || true"
$SSH "docker run -d \
  --name openemr-seed \
  --network $NETWORK \
  -e MYSQL_HOST=mysql \
  -e MYSQL_ROOT_PASS=root \
  -e MYSQL_USER=openemr \
  -e MYSQL_PASS=openemr \
  -e OE_USER=admin \
  -e OE_PASS=pass \
  -v ${SITE_VOLUME}:/var/www/localhost/htdocs/openemr/sites \
  openemr/openemr:flex"

echo "==> Waiting for dev container to be ready..."
$SSH 'for i in $(seq 1 90); do
  if docker exec openemr-seed curl -sf --insecure https://localhost/ -o /dev/null 2>/dev/null; then
    echo "    Dev container ready."
    exit 0
  fi
  echo "    Waiting... ($i/90)"
  sleep 5
done
echo "ERROR: Dev container did not become ready in time"
exit 1'

# ---------------------------------------------------------------------------
# 2. Import random patients via Synthea (devtools handles everything)
# ---------------------------------------------------------------------------
echo "==> Importing ${PATIENT_COUNT} random patients via Synthea..."
echo "    (This takes several seconds per patient)"
$SSH "docker exec openemr-seed /root/devtools import-random-patients $PATIENT_COUNT"

# ---------------------------------------------------------------------------
# 3. Create 5 hospital facilities via SQL
# ---------------------------------------------------------------------------
echo "==> Creating 5 hospital facilities..."
$SSH "$MYSQL -e '
INSERT INTO facility (name, phone, street, city, state, postal_code, country_code, federal_ein, facility_npi, facility_taxonomy, facility_code, domain_identifier)
VALUES
  (\"Riverside General Hospital\",    \"415-555-0101\", \"1200 Market Street\",  \"San Francisco\", \"CA\", \"94102\", \"US\", \"94-1234567\", \"1234567890\", \"282N00000X\", \"RGH\",  \"riverside-general\"),
  (\"Cedar Park Medical Center\",     \"415-555-0102\", \"800 Cedar Avenue\",    \"Oakland\",       \"CA\", \"94607\", \"US\", \"94-2345678\", \"2345678901\", \"282N00000X\", \"CPMC\", \"cedar-park-medical\"),
  (\"Bay Area Community Hospital\",   \"415-555-0103\", \"350 Bay Shore Blvd\",  \"San Mateo\",     \"CA\", \"94401\", \"US\", \"94-3456789\", \"3456789012\", \"282N00000X\", \"BACH\", \"bay-area-community\"),
  (\"Golden Gate Regional Medical\",  \"415-555-0104\", \"2100 Post Street\",    \"San Francisco\", \"CA\", \"94115\", \"US\", \"94-4567890\", \"4567890123\", \"282N00000X\", \"GGRM\", \"golden-gate-regional\"),
  (\"Pacific Heights Health Center\", \"415-555-0105\", \"1900 Pacific Avenue\", \"San Francisco\", \"CA\", \"94109\", \"US\", \"94-5678901\", \"5678901234\", \"282N00000X\", \"PHHC\", \"pacific-heights\");
'"

# ---------------------------------------------------------------------------
# 4. Distribute patients across the 5 facilities (round-robin)
#    patient_data.care_team_facility stores facility ID as text
#    form_encounter.facility_id stores it as int
# ---------------------------------------------------------------------------
echo "==> Distributing patients across facilities..."
$SSH "$MYSQL -e '
SET @f1 = (SELECT id FROM facility WHERE facility_code=\"RGH\"  LIMIT 1);
SET @f2 = (SELECT id FROM facility WHERE facility_code=\"CPMC\" LIMIT 1);
SET @f3 = (SELECT id FROM facility WHERE facility_code=\"BACH\" LIMIT 1);
SET @f4 = (SELECT id FROM facility WHERE facility_code=\"GGRM\" LIMIT 1);
SET @f5 = (SELECT id FROM facility WHERE facility_code=\"PHHC\" LIMIT 1);

UPDATE patient_data SET care_team_facility = CAST(@f1 AS CHAR) WHERE MOD(pid, 5) = 0 AND (care_team_facility IS NULL OR care_team_facility = \"\");
UPDATE patient_data SET care_team_facility = CAST(@f2 AS CHAR) WHERE MOD(pid, 5) = 1 AND (care_team_facility IS NULL OR care_team_facility = \"\");
UPDATE patient_data SET care_team_facility = CAST(@f3 AS CHAR) WHERE MOD(pid, 5) = 2 AND (care_team_facility IS NULL OR care_team_facility = \"\");
UPDATE patient_data SET care_team_facility = CAST(@f4 AS CHAR) WHERE MOD(pid, 5) = 3 AND (care_team_facility IS NULL OR care_team_facility = \"\");
UPDATE patient_data SET care_team_facility = CAST(@f5 AS CHAR) WHERE MOD(pid, 5) = 4 AND (care_team_facility IS NULL OR care_team_facility = \"\");
'"

# ---------------------------------------------------------------------------
# 5. Assign encounters to patient facilities
# ---------------------------------------------------------------------------
echo "==> Assigning encounters to patient facilities..."
$SSH "$MYSQL -e '
UPDATE form_encounter fe
JOIN patient_data pd ON fe.pid = pd.pid
SET fe.facility_id = CAST(pd.care_team_facility AS UNSIGNED)
WHERE (fe.facility_id = 0 OR fe.facility_id IS NULL)
  AND pd.care_team_facility IS NOT NULL
  AND pd.care_team_facility != \"\";
'"

# ---------------------------------------------------------------------------
# 6. Verify
# ---------------------------------------------------------------------------
echo "==> Verifying seed data..."
$SSH "$MYSQL -e '
SELECT \"Patients\" AS entity, COUNT(*) AS total FROM patient_data
UNION ALL SELECT \"Encounters\", COUNT(*) FROM form_encounter
UNION ALL SELECT \"Conditions\", COUNT(*) FROM lists WHERE type=\"medical_problem\"
UNION ALL SELECT \"Allergies\", COUNT(*) FROM lists WHERE type=\"allergy\"
UNION ALL SELECT \"Medications\", COUNT(*) FROM lists WHERE type=\"medication\"
UNION ALL SELECT \"Vitals\", COUNT(*) FROM form_vitals
UNION ALL SELECT \"Immunizations\", COUNT(*) FROM immunizations;

SELECT f.name AS facility, COUNT(pd.pid) AS patients
FROM facility f
LEFT JOIN patient_data pd ON pd.care_team_facility = CAST(f.id AS CHAR)
WHERE f.facility_code IN (\"RGH\",\"CPMC\",\"BACH\",\"GGRM\",\"PHHC\")
GROUP BY f.id, f.name;
'"

# ---------------------------------------------------------------------------
# 7. Clean up the throwaway container
# ---------------------------------------------------------------------------
echo "==> Removing throwaway dev container..."
$SSH "docker stop openemr-seed && docker rm openemr-seed 2>/dev/null || true"

echo ""
echo "==> Seed complete! ${PATIENT_COUNT} patients across 5 facilities."
echo "    Verify at: https://openemr.g4.techopswhiz.com"
