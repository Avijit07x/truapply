import type { JobFilter } from "../api/types";
import { isGroup } from "./groups";
import { isStatus } from "./status";

export function jobFilter(params: URLSearchParams): JobFilter {
  const status = params.get("status");
  const group = params.get("group");
  if (isGroup(group)) {
    return { group };
  }
  return isStatus(status) ? { status } : {};
}
