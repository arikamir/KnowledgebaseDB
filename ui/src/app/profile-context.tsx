import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export interface EditableProfile {
  role: string;
  experienceLevel: string;
  targetRole: string;
  availableTimePerWeek: number;
}

interface ProfileContextValue {
  profile: EditableProfile;
  setProfile: (profile: EditableProfile) => void;
}

const INITIAL_PROFILE: EditableProfile = { role: "", experienceLevel: "", targetRole: "", availableTimePerWeek: 0 };
const ProfileContext = createContext<ProfileContextValue | null>(null);

export function ProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState(INITIAL_PROFILE);
  const value = useMemo(() => ({ profile, setProfile }), [profile]);
  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useProfile(): ProfileContextValue {
  const value = useContext(ProfileContext);
  if (!value) throw new Error("PROFILE_PROVIDER_REQUIRED");
  return value;
}
