export class MessageUpsert {
    public static async run(message: any) {
        console.log(JSON.stringify(message, undefined, 2))
    }
}