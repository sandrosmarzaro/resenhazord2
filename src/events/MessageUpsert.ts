export class MessageUpsert {
    public static async run() {
        return async (message: any) => {
            console.log(JSON.stringify(message, undefined, 2))
        }
    }
}