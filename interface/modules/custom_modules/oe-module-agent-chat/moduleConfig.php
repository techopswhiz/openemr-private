<?php

/**
 * Clinical Agent Chat Module Configuration
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    Menashe Homnick <menasheh@gmail.com>
 * @copyright Copyright (c) 2026 Menashe Homnick <menasheh@gmail.com>
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

return [
    'name' => 'Clinical Agent Chat',
    'description' => 'Floating chat bubble that provides access to the clinical AI agent from anywhere in the OpenEMR interface.',
    'version' => '1.0.0',
    'author' => 'Menashe Homnick',
    'email' => 'menasheh@gmail.com',
    'license' => 'GPL-3.0',

    'require' => [
        'openemr' => '>=7.0.0',
    ],
];
