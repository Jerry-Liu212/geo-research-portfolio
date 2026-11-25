export type AIProviderName =
  | "mock"
  | "openai"
  | "doubao"
  | "deepseek"
  | "kimi";

export type AskAIInput = {
  brandName: string;
  question: string;
};

export type AIAnswer = {
  provider: AIProviderName;
  model: string;
  text: string;
};

export interface AIProvider {
  ask(input: AskAIInput): Promise<AIAnswer>;
}

export type AIProviderConfig = {
  provider: AIProviderName;
  model: string;
};
