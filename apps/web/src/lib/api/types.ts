/**
 * Types mirroring the FastAPI response contract (docs/API_CONVENTIONS.md).
 *
 * Money is transported as an exact integer in minor units plus a decimal
 * string. The frontend formats it for display and never does arithmetic on
 * the decimal string — that is what `minorUnits` is for.
 */

export interface SuccessEnvelope<TBody> {
  success: true;
  message: string;
  body: TBody;
  request_id: string | null;
}

export interface ErrorEnvelope {
  success: false;
  error: {
    code: ApiErrorCode;
    message: string;
    details: Record<string, unknown> | null;
  };
  request_id: string | null;
}

export type Envelope<TBody> = SuccessEnvelope<TBody> | ErrorEnvelope;

/** Stable error codes the UI may branch on. Keep in step with the backend. */
export type ApiErrorCode =
  | "VALIDATION_ERROR"
  | "AUTH_REQUIRED"
  | "AUTH_INVALID"
  | "PERMISSION_DENIED"
  | "RESOURCE_NOT_FOUND"
  | "CONFLICT"
  | "CONFIRMATION_REQUIRED"
  | "RATE_LIMITED"
  | "AI_PROVIDER_UNAVAILABLE"
  | "AGENT_NOT_AVAILABLE"
  | "INTERNAL_ERROR";

export interface Money {
  minor_units: number;
  currency: string;
  amount: string;
}

export interface Account {
  account_id: string;
  account_type: "current" | "savings" | "card";
  status: "active" | "frozen" | "closed";
  label: string;
  iban_suffix: string;
  balance: Money;
  available_balance: Money;
}

export interface AssistantReply {
  reply: string;
  agent_id: string;
  intent: string;
  conversation_id: string | null;
  citations: string[];
  data: Record<string, unknown>;
  pending_confirmation: Record<string, unknown> | null;
}
