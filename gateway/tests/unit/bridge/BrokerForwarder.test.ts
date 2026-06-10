import { describe, it, expect, vi, beforeEach } from 'vitest';

import BrokerForwarder from '../../../src/bridge/BrokerForwarder.js';
import CommandPublisher from '../../../src/bridge/CommandPublisher.js';
import InFlightCommands from '../../../src/bridge/InFlightCommands.js';
import ReactMessage from '../../../src/utils/ReactMessage.js';
import TypingIndicator from '../../../src/utils/TypingIndicator.js';
import GetGroupExpiration from '../../../src/utils/GetGroupExpiration.js';
import { GroupCommandData } from '../../fixtures/index.js';

function makePublisher(id = 'corr-1'): CommandPublisher {
  return { publish: vi.fn().mockResolvedValue(id) } as unknown as CommandPublisher;
}

describe('BrokerForwarder', () => {
  beforeEach(() => {
    vi.spyOn(ReactMessage, 'run').mockResolvedValue(undefined);
    vi.spyOn(TypingIndicator, 'start').mockResolvedValue(undefined);
    vi.spyOn(TypingIndicator, 'stop').mockResolvedValue(undefined);
    vi.spyOn(GetGroupExpiration, 'run').mockResolvedValue(undefined);
  });

  it('reacts and starts typing before publishing', async () => {
    const publisher = makePublisher();
    const data = GroupCommandData.build();

    await new BrokerForwarder(publisher, new InFlightCommands()).forward(data, ',ping');

    expect(ReactMessage.run).toHaveBeenCalledWith(data);
    expect(TypingIndicator.start).toHaveBeenCalledWith(data.key.remoteJid);
  });

  it('publishes the command with the resolved text', async () => {
    const publisher = makePublisher();
    const data = GroupCommandData.build();

    await new BrokerForwarder(publisher, new InFlightCommands()).forward(data, ',ping');

    const [commandData] = (publisher.publish as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(commandData.text).toBe(',ping');
  });

  it('tracks the correlation id against the jid', async () => {
    const publisher = makePublisher('corr-42');
    const inFlight = new InFlightCommands();
    const data = GroupCommandData.build();

    await new BrokerForwarder(publisher, inFlight).forward(data, ',ping');

    expect(inFlight.resolve('corr-42')).toBe(data.key.remoteJid);
  });

  it('stops typing and does not track when the publish fails', async () => {
    const publisher = {
      publish: vi.fn().mockRejectedValue(new Error('broker down')),
    } as unknown as CommandPublisher;
    const inFlight = new InFlightCommands();
    const data = GroupCommandData.build();

    await new BrokerForwarder(publisher, inFlight).forward(data, ',ping');

    expect(TypingIndicator.stop).toHaveBeenCalledWith(data.key.remoteJid);
    expect(inFlight.resolve('corr-1')).toBeUndefined();
  });
});
