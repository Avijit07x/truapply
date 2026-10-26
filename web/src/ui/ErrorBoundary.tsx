import { Component, type ReactNode } from "react";
import { messageOf } from "../api/client";
import { Row } from "./Blocks";
import { Button } from "./Button";
import { Callout } from "./Callout";

type Props = { resetKey: string; onReset: () => void; children: ReactNode };
type State = { error: unknown };

export class ErrorBoundary extends Component<Props, State> {
  override state: State = { error: null };

  static getDerivedStateFromError(error: unknown): State {
    return { error };
  }

  override componentDidUpdate(previous: Props) {
    if (previous.resetKey !== this.props.resetKey && this.state.error !== null) {
      this.setState({ error: null });
    }
  }

  retry = () => {
    this.props.onReset();
    this.setState({ error: null });
  };

  override render() {
    if (this.state.error === null) {
      return this.props.children;
    }
    return (
      <Callout tone="bad">
        <p>{messageOf(this.state.error)}</p>
        <Row>
          <Button onClick={this.retry}>Try again</Button>
        </Row>
      </Callout>
    );
  }
}
