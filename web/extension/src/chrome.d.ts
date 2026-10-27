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
    function create(properties: { url: string; active: boolean }): Promise<Tab>;
    function remove(tabId: number): Promise<void>;
    function update(tabId: number, properties: { url: string }): Promise<Tab>;
  }
  namespace alarms {
    type Alarm = { name: string };
    function create(
      name: string,
      info: { when?: number; delayInMinutes?: number; periodInMinutes?: number },
    ): Promise<void>;
    function get(name: string): Promise<Alarm | undefined>;
    function clear(name: string): Promise<boolean>;
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
    const local: {
      get(key: string): Promise<Record<string, unknown>>;
      set(items: Record<string, unknown>): Promise<void>;
      remove(key: string): Promise<void>;
    };
  }
}
