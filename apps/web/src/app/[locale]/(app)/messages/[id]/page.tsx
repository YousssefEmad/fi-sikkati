import { ThreadPage } from "@/features/chat/thread-page";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ThreadPage conversationId={id} />;
}
