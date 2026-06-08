config = {
    "name": "SendMessage",
    "type": "api",
    "path": "/messages",
    "method": "POST",
    "emits": ["message.sent"]
}
 
async def handler(req, ctx):
    await ctx.emit({
        "topic": "message.sent",
        "data": {"text": req.body["text"]}
    })
    return {"status": 200, "body": {"ok": True}}
