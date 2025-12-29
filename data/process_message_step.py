config = {
    "name": "ProcessMessage",
    "type": "event",
    "subscribes": ["message.sent"]
}
 
async def handler(input, ctx):
    ctx.logger.info("Processing message", input)
