<?php

/**
 * Clinical Agent Chat Module Bootstrap
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    Menashe Homnick <menasheh@gmail.com>
 * @copyright Copyright (c) 2026 Menashe Homnick <menasheh@gmail.com>
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

use OpenEMR\Core\ModulesClassLoader;
use OpenEMR\Core\OEGlobalsBag;
use OpenEMR\Modules\AgentChat\Bootstrap;

$file = OEGlobalsBag::getInstance()->get('fileroot');
$classLoader = new ModulesClassLoader($file);
$classLoader->registerNamespaceIfNotExists('OpenEMR\\Modules\\AgentChat\\', __DIR__ . DIRECTORY_SEPARATOR . 'src');

$eventDispatcher = OEGlobalsBag::getInstance()->get('kernel')->getEventDispatcher();
$bootstrap = new Bootstrap($eventDispatcher);
$bootstrap->subscribeToEvents();
