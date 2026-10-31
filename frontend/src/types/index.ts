export interface User { id: string; full_name: string; email: string }
export interface TokenResponse { access_token: string; token_type: string; expires_at: string; user: User }

export type ExperienceLevel = "fresher" | "internship" | "0-1" | "1-3" | "3-5" | "5+";
export type EducationLevel = "high_school" | "diploma" | "bachelors" | "masters" | "phd" | "other";

export interface Profile {
  full_name: string;
  email: string;
  photo_url: string | null;
  phone: string | null;
  location: string | null;
  linkedin_url: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  degree: string | null;
  university: string | null;
  graduation_year: number | null;
  education_level: EducationLevel | null;
  experience_level: ExperienceLevel | null;
  target_role: string | null;
  profile_complete: boolean;
  missing_fields: string[];
}

export type ProfileUpdate = Partial<Omit<Profile, "email" | "photo_url" | "profile_complete" | "missing_fields">>;
