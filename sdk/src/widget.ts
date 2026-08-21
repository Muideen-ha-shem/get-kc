import { fetchWorkspaceConfig, getOrCreateSessionId, sendChatMessage } from './client';
import {
  appendErrorMessage,
  appendMessage,
  appendQuickActionChips,
  appendSuggestionCards,
  applyPrimaryColor,
  applyReserveLeft,
  applyTheme,
  buildPanel,
  createShadowHost,
} from './renderer';
import type { QuickAction, ResolvedConfig, WorkspaceConfigResponse } from './types';

/** The currently-mounted panel, if any — one widget per page (same
 * assumption `renderer.ts`'s singleton `HOST_ID` shadow host already
 * makes), set at the end of `mountWidget()` so a host page's own UI
 * (e.g. a sidebar "Intelligence Layer" button) can open/close the panel
 * itself via `HavisIQ.open()`/`close()`, not just the SDK's own internal
 * floating toggle. */
let activePanel: HTMLElement | null = null;

export function openPanel(): void {
  if (!activePanel) {
    console.warn('HavisIQ.open(): called before HavisIQ.init() finished mounting the widget.');
    return;
  }
  activePanel.classList.add('havisiq-open');
}

export function closePanel(): void {
  activePanel?.classList.remove('havisiq-open');
}

/** Orchestrates SDK init → resolve config → render → wire events.
 *
 * Only `floating` mode is implemented this phase. Any other mode logs a
 * warning and falls back to floating rather than rendering nothing —
 * `inline`/`popup`/`fullscreen` are named extension points for a later
 * phase, not empty stubs pretending to work. */
export async function mountWidget(config: ResolvedConfig): Promise<void> {
  if (config.mode !== 'floating') {
    console.warn(
      `HavisIQ: mode "${config.mode}" is not yet implemented (planned for a later phase); falling back to "floating".`,
    );
  }

  const { root } = createShadowHost(config.position);
  applyTheme(root, config.theme);
  applyReserveLeft(root, config.reserveLeft);

  let workspace: WorkspaceConfigResponse | null = null;
  let loadError: string | null = null;
  try {
    workspace = await fetchWorkspaceConfig(config);
  } catch (error) {
    loadError = error instanceof Error ? error.message : 'Failed to load HavisIQ configuration.';
  }

  applyPrimaryColor(root, workspace?.primaryColor);
  const { panel, messageList, input, sendButton, suggestedRow, suggestionList, colCenter, scrollArea } = buildPanel(
    root,
    { name: workspace?.name, welcomeMessage: workspace?.welcomeMessage },
    config.context,
  );

  if (loadError) {
    appendErrorMessage(messageList, loadError);
  } else {
    const actions: QuickAction[] = workspace?.quickActions ?? [];
    const onSelect = (prompt: string) => {
      input.value = prompt;
      void submit(prompt);
    };
    appendQuickActionChips(suggestedRow, actions, onSelect);
    appendSuggestionCards(suggestionList, actions, onSelect);
  }

  const sessionId = getOrCreateSessionId();

  function scrollToLatest(): void {
    scrollArea.scrollTop = scrollArea.scrollHeight;
  }

  async function submit(message: string): Promise<void> {
    if (!message.trim()) return;
    // The greeting/suggestions only make sense before a real
    // conversation exists — once the first message goes out, the
    // transcript takes over the scroll area instead of sitting below it.
    colCenter.classList.add('havisiq-active');
    appendMessage(messageList, { role: 'user', text: message });
    scrollToLatest();
    input.value = '';
    sendButton.disabled = true;
    try {
      const response = await sendChatMessage(config, message, sessionId);
      appendMessage(messageList, { role: 'assistant', text: response.answer });
    } catch (error) {
      appendErrorMessage(
        messageList,
        error instanceof Error ? error.message : 'Something went wrong. Please try again.',
      );
    } finally {
      sendButton.disabled = false;
      scrollToLatest();
    }
  }

  const form = panel.querySelector('.havisiq-form') as HTMLFormElement;
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    void submit(input.value);
  });

  const helpLink = panel.querySelector('.havisiq-help-link') as HTMLButtonElement;
  helpLink.addEventListener('click', () => void submit('How do I use this platform?'));

  activePanel = panel;
}
