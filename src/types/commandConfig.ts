export enum ArgType {
  None = 'none',
  Required = 'required',
  Optional = 'optional',
}

export interface OptionDef {
  name: string;
  values?: string[];
  pattern?: string;
}

export interface CommandConfig {
  name: string;
  aliases?: string[];
  flags?: string[];
  options?: OptionDef[];
  args?: ArgType;
  argsPattern?: RegExp;
  groupOnly?: boolean;
}

export interface ParsedCommand {
  commandName: string;
  flags: Set<string>;
  options: Map<string, string>;
  rest: string;
}
