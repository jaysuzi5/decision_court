import { useEffect, useState } from "react";
import { fetchMe, type Me } from "./api";

export function useMe() {
  const [me, setMe] = useState<Me | null>(null);
  useEffect(() => {
    fetchMe().then(setMe);
  }, []);
  return me;
}
