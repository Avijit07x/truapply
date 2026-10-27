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
