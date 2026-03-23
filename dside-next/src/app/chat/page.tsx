"use client";

import ChatInterface from "@/components/ChatInterface";

export default function ChatPage() {
  return (
    <div className="mx-auto max-w-3xl h-[calc(100vh-57px-64px)] sm:h-[calc(100vh-57px)] flex flex-col">
      <ChatInterface />
    </div>
  );
}
