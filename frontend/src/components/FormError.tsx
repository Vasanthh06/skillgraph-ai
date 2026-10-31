export default function FormError({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="whitespace-pre-line rounded-md bg-red-50 px-3 py-2 text-sm text-alert">
      {message}
    </p>
  );
}
