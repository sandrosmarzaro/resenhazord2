// Command triggers (names and aliases) safe to route over the broker today: pure
// text replies, no mid-command wa_call, no media. The set grows as the broker path
// proves out; everything else stays on the WebSocket during the parallel run.
export const BROKER_COMMANDS = new Set(['oi', 'hi', 'd20']);
