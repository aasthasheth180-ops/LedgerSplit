import { useRef, useState } from "react";

export function useAuthSubmission() {
  const submissionRef = useRef(false);
  const [isLoading, setIsLoading] = useState(false);

  function beginSubmission(): boolean {
    if (submissionRef.current) {
      return false;
    }

    submissionRef.current = true;
    setIsLoading(true);

    return true;
  }

  function endSubmission(): void {
    submissionRef.current = false;
    setIsLoading(false);
  }

  return {
    isLoading,
    beginSubmission,
    endSubmission,
  };
}
