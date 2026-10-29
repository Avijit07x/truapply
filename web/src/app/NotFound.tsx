import { Link } from "../lib/router";
import { PageHeader } from "../ui/Blocks";

export function NotFound() {
  return <PageHeader title="Page not found" description={<Link to="/">Go to Today</Link>} />;
}
