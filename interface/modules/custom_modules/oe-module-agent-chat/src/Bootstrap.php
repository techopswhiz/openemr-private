<?php

/**
 * Clinical Agent Chat Module Bootstrap Class
 *
 * Registers the floating chat widget on the main tabs page
 * via EVENT_BODY_RENDER_POST, following the same pattern as
 * the faxsms phone widget.
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    Menashe Homnick <menasheh@gmail.com>
 * @copyright Copyright (c) 2026 Menashe Homnick <menasheh@gmail.com>
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

namespace OpenEMR\Modules\AgentChat;

use OpenEMR\Common\Logging\SystemLogger;
use OpenEMR\Common\Twig\TwigContainer;
use OpenEMR\Core\OEGlobalsBag;
use OpenEMR\Events\Main\Tabs\RenderEvent;
use Symfony\Component\EventDispatcher\EventDispatcherInterface;

class Bootstrap
{
    private \Twig\Environment $twig;

    public function __construct(
        private readonly EventDispatcherInterface $eventDispatcher
    ) {
        $twig = new TwigContainer($this->getTemplatePath());
        $this->twig = $twig->getTwig();
    }

    public function getTemplatePath(): string
    {
        return dirname(__DIR__) . DIRECTORY_SEPARATOR . 'templates' . DIRECTORY_SEPARATOR;
    }

    public function subscribeToEvents(): void
    {
        $this->eventDispatcher->addListener(
            RenderEvent::EVENT_BODY_RENDER_POST,
            $this->renderChatWidget(...)
        );
    }

    public function renderChatWidget(RenderEvent $event): void
    {
        try {
            $agentUrl = OEGlobalsBag::getInstance()->get('web_root') . '/agent/';
            echo $this->twig->render('chat_widget.html.twig', [
                'agentUrl' => $agentUrl,
            ]);
        } catch (\Throwable $e) {
            (new SystemLogger())->error(
                'AgentChat: Error rendering chat widget',
                ['error' => $e->getMessage()]
            );
        }
    }
}
