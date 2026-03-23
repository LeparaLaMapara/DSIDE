import { NextRequest } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import type { ChatMessage, UserProfile } from "@/types";

const SYSTEM_PROMPT = `You are a career advisor for young South Africans. You have deep knowledge of: the South African job market, SETA learnerships, TVET colleges, scarce skills, youth employment programs like YES4Youth and Harambee, and government services like UIF and SAYouth.mobi. Always give specific, actionable advice. Mention real programs, real websites, real organizations. Be encouraging but honest. If you don't know something specific, say so and suggest where to find the information. Keep responses concise and practical.

Key resources you should reference when relevant:
- SAYouth.mobi (free, works on any phone) - government youth portal
- YES4Youth (yes4youth.co.za) - paid work experience programme
- Harambee Youth Employment Accelerator (harambee.co.za) - free skills & job matching
- National Youth Development Agency (nyda.gov.za) - grants, mentorship, career guidance
- SETA learnerships (various sector SETAs) - paid learning + work experience
- TVET colleges - affordable technical/vocational training
- National Student Financial Aid Scheme (NSFAS) - funding for higher education
- Sector-specific opportunities from MICT SETA, HWSETA, CETA, AgriSETA, etc.

Format your responses clearly. Use bullet points for lists. Keep paragraphs short for mobile readability.`;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { messages, userProfile }: { messages: ChatMessage[]; userProfile?: UserProfile } = body;

    if (!messages || messages.length === 0) {
      return new Response(JSON.stringify({ error: "No messages provided" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      // Return a helpful fallback response when API key isn't configured
      const fallbackResponse =
        "I'm currently running in offline mode. Here are some immediate steps you can take:\n\n" +
        "1. **SAYouth.mobi** - Register for free (works on any phone, no data needed)\n" +
        "2. **YES4Youth** (yes4youth.co.za) - Apply for paid work experience\n" +
        "3. **Harambee** (harambee.co.za) - Free skills assessment and job matching\n" +
        "4. **NYDA** (nyda.gov.za) - Visit your nearest branch for career guidance\n\n" +
        "Please try again later when the advisor is fully connected.";

      return new Response(fallbackResponse, {
        headers: { "Content-Type": "text/plain" },
      });
    }

    const client = new Anthropic({ apiKey });

    // Build system prompt with user context
    let systemPrompt = SYSTEM_PROMPT;
    if (userProfile) {
      systemPrompt += `\n\nUser context: Province: ${userProfile.province || "Unknown"}, Education: ${userProfile.education || "Unknown"}, Interests: ${userProfile.interests?.join(", ") || "Unknown"}. Tailor your advice to their specific situation.`;
    }

    // Create streaming response
    const stream = await client.messages.stream({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1024,
      system: systemPrompt,
      messages: messages.map((m) => ({
        role: m.role,
        content: m.content,
      })),
    });

    // Convert to a ReadableStream for the response
    const encoder = new TextEncoder();
    const readableStream = new ReadableStream({
      async start(controller) {
        try {
          for await (const event of stream) {
            if (
              event.type === "content_block_delta" &&
              event.delta.type === "text_delta"
            ) {
              controller.enqueue(encoder.encode(event.delta.text));
            }
          }
          controller.close();
        } catch (err) {
          controller.error(err);
        }
      },
    });

    return new Response(readableStream, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Transfer-Encoding": "chunked",
      },
    });
  } catch (error) {
    console.error("Chat API error:", error);
    return new Response(
      "Sorry, something went wrong. Please try again in a moment.",
      {
        status: 500,
        headers: { "Content-Type": "text/plain" },
      }
    );
  }
}
