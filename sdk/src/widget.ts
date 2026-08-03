import { fetchWorkspaceConfig, getOrCreateSessionId, sendChatMessage } from './client';
import {
  appendErrorMessage,
  appendMessage,
  appendQuickActionChips,
  applyTheme,
  buildPanel,
  buildToggleButton,
  createShadowHost,
} from './renderer';
import type { ResolvedConfig, WorkspaceConfigResponse } from './types';

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

  let workspace: WorkspaceConfigResponse | null = null;
  let loadError: string | null = null;
  try {
    workspace = await fetchWorkspaceConfig(config);
  } catch (error) {
    loadError = error instanceof Error ? error.message : 'Failed to load HavisIQ configuration.';
  }

  buildToggleButton(root, workspace?.primaryColor);
  const { panel, messageList, input, sendButton } = buildPanel(root, {
    logo: workspace?.logo,
    name: workspace?.name,
    welcomeMessage: workspace?.welcomeMessage,
  });

  if (loadError) {
    appendErrorMessage(messageList, loadError);
  } else if (workspace?.quickActions?.length) {
    appendQuickActionChips(panel, workspace.quickActions, (prompt) => {
      input.value = prompt;
      void submit(prompt);
    });
  }

  const sessionId = getOrCreateSessionId();

  async function submit(message: string): Promise<void> {
    if (!message.trim()) return;
    appendMessage(messageList, { role: 'user', text: message });
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
    }
  }

  const toggle = root.querySelector('.havisiq-toggle') as HTMLButtonElement;
  toggle.addEventListener('click', () => {
    panel.classList.toggle('havisiq-open');
  });

  const form = panel.querySelector('.havisiq-form') as HTMLFormElement;
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    void submit(input.value);
  });
}
