import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';
import { Sentry } from '../infra/Sentry.js';
import type { RestCountry } from '../types/commands/restcountries.js';

const REGION_MAP: Record<string, { emoji: string; label: string }> = {
  Africa: { emoji: '🌍', label: 'África' },
  Americas: { emoji: '🌎', label: 'Américas' },
  Antarctic: { emoji: '🌐', label: 'Antártida' },
  Asia: { emoji: '🌏', label: 'Ásia' },
  Europe: { emoji: '🌍', label: 'Europa' },
  Oceania: { emoji: '🌏', label: 'Oceania' },
};

const SUBREGION_PT: Record<string, string> = {
  'South America': 'América do Sul',
  'North America': 'América do Norte',
  'Central America': 'América Central',
  Caribbean: 'Caribe',
  'Northern Africa': 'África do Norte',
  'Western Africa': 'África Ocidental',
  'Eastern Africa': 'África Oriental',
  'Middle Africa': 'África Central',
  'Southern Africa': 'África Austral',
  'Western Europe': 'Europa Ocidental',
  'Northern Europe': 'Europa do Norte',
  'Eastern Europe': 'Europa do Leste',
  'Southern Europe': 'Europa do Sul',
  'Central Asia': 'Ásia Central',
  'Western Asia': 'Ásia Ocidental',
  'Eastern Asia': 'Ásia Oriental',
  'South Asia': 'Sul da Ásia',
  'Southeast Asia': 'Sudeste Asiático',
  Melanesia: 'Melanésia',
  Micronesia: 'Micronésia',
  Polynesia: 'Polinésia',
  'Australia and New Zealand': 'Austrália e Nova Zelândia',
};

const API_URL =
  'https://restcountries.com/v3.1/all?fields=name,flags,flag,capital,region,subregion,population,area,languages,currencies';

export default class CountryFlagCommand extends Command {
  readonly config: CommandConfig = {
    name: 'bandeira',
    flags: ['show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Envia a bandeira de um país aleatório com informações.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    try {
      const response = await AxiosClient.get<RestCountry[]>(API_URL);
      const countries = response.data;
      const country = countries[Math.floor(Math.random() * countries.length)];
      const caption = CountryFlagCommand.buildCaption(country);
      return [Reply.to(data).image(country.flags.png, caption)];
    } catch (error) {
      Sentry.captureException(error, { extra: { command: 'bandeira' } });
      return [Reply.to(data).text('Erro ao buscar bandeira. Tente novamente mais tarde! 🌍')];
    }
  }

  private static buildCaption(country: RestCountry): string {
    const region = REGION_MAP[country.region] ?? { emoji: '🌐', label: country.region };
    const subregion = country.subregion
      ? (SUBREGION_PT[country.subregion] ?? country.subregion)
      : null;
    const locationLine = subregion
      ? `${region.emoji} ${region.label} · ${subregion}`
      : `${region.emoji} ${region.label}`;

    const capital = country.capital?.[0] ?? 'N/A';
    const population = country.population.toLocaleString('pt-BR');
    const area = Math.round(country.area).toLocaleString('pt-BR');
    const languages = Object.values(country.languages ?? {}).join(', ') || 'N/A';
    const currencies =
      Object.entries(country.currencies ?? {})
        .map(([code, c]) => `${c.name} (${code})`)
        .join(' / ') || 'N/A';

    const lines: string[] = [];
    lines.push(`*${country.name.common}* ${country.flag}`);
    if (country.name.official !== country.name.common) {
      lines.push(`_${country.name.official}_`);
    }
    lines.push('');
    lines.push(locationLine);
    lines.push(`🏙️ Capital: ${capital}`);
    lines.push(`👥 ${population} habitantes`);
    lines.push(`📐 ${area} km²`);
    lines.push(`🗣️ ${languages}`);
    lines.push(`💰 ${currencies}`);

    return lines.join('\n');
  }
}
