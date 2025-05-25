"use client"

import { Send } from "lucide-react"
import * as React from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { BaseMessage } from "@/lib/apiTypes"
import { ChatMessage } from "@/components/ChatMessage"

interface CardsChatProps {
  messages: Array<BaseMessage>
  onSendMessage: (message: string) => void
}

export function CardsChat({ messages, onSendMessage }: CardsChatProps) {
  const [input, setInput] = React.useState("")
  const inputLength = input.trim().length

  return (
    <Card className="flex flex-col w-full h-full">
      <CardHeader className="w-full flex justify-center py-4">
        <h2 className="text-xl font-semibold text-accent">Ask me anything</h2>
      </CardHeader>
      <CardContent className="flex-1 overflow-auto">
        <div className="space-y-4">
          {messages.map((message: BaseMessage, index: number) => (
            <ChatMessage key={index} message={message} />
          ))}
        </div>
      </CardContent>
      <CardFooter>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (inputLength === 0) return
            onSendMessage(input)
            setInput("")
          }}
          className="flex w-full items-center space-x-2"
        >
          <Input
            id="message"
            placeholder="Type your message..."
            className="flex-1"
            autoComplete="off"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <Button type="submit" size="icon" disabled={inputLength === 0}>
            <Send />
            <span className="sr-only">Send</span>
          </Button>
        </form>
      </CardFooter>
    </Card>
  )
}
