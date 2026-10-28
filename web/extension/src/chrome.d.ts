declare namespace chrome {
  namespace runtime {
    type MessageSender = { tab?: { id?: number } };
    function sendMessage<T>(message: unknown): Promise<T>;
    const onMessage: {
      addListener(
        listener: (
          message: unknown,
          sender: MessageSender,
          reply: (answer: unknown) => void,
        ) => boolean,
      ): void;
    };
  }
  namespace tabs {
    type Tab = { id?: number; url?: string };
    function create(options: { url: string; active: boolean }): Promise<Tab>;
    function get(tabId: number): Promise<Tab>;
    function remove(tabId: number): Promise<void>;
    const onRemoved: { addListener(listener: (tabId: number) => void): void };
  }
  namespace alarms {
    type Alarm = { name: string };
    function create(name: string, info: { periodInMinutes: number }): Promise<void>;
    function get(name: string): Promise<Alarm | undefined>;
    const onAlarm: { addListener(listener: (alarm: Alarm) => void): void };
  }
  namespace action {
    const onClicked: { addListener(listener: (tab: tabs.Tab) => void): void };
  }
  namespace scripting {
    function executeScript(injection: {
      target: { tabId: number };
      files: string[];
      world?: "MAIN" | "ISOLATED";
    }): Promise<unknown[]>;
  }
  namespace storage {
    const session: {
      get(key: string): Promise<Record<string, unknown>>;
      set(items: Record<string, unknown>): Promise<void>;
      remove(key: string): Promise<void>;
    };
    const local: {
      get(key: string): Promise<Record<string, unknown>>;
      set(items: Record<string, unknown>): Promise<void>;
      remove(key: string): Promise<void>;
    };
  }
}
