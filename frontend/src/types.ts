export type SkillLevel = 'beginner' | 'intermediate' | 'advanced';
export type Skill = { name: string; level: SkillLevel; category?: string };
export type Project = { id?: number; name: string; description: string; technologies: string[]; domain: string; source_url?: string };
export type Profile = {
  name: string; email: string; education: string; degree: string; branch: string;
  graduation_year: number | null; experience_level: SkillLevel | null; target_role: string;
  preferred_industry: string; skills: Skill[]; soft_skills: string[]; projects: Project[];
  certifications: { name: string; platform: string; year: number | null }[];
  interests: { name: string; source: 'user' | 'ai_inferred'; score: number }[];
};
export type Factor = { key: string; label: string; weight: number; score: number; contribution: number; evidence: string[] };
export type SkillProgress = { name: string; current_level: string; required_level: string; score: number; severity: 'high' | 'medium' | 'low'; required: boolean };
export type CareerRecommendation = {
  career_id: number; slug: string; career: string; score: number; factors: Factor[];
  evidence: string[]; matched_skills: string[]; missing_skills: string[];
  relevant_projects: string[]; skill_progress: SkillProgress[]; readiness: number; coverage: number;
};
export type LearningResource = { id: string; title: string; provider: string; url: string; summary: string; reviewed_on: string };
export type RoadmapItem = { id: number; phase: string; title: string; description: string; status: 'not_started' | 'in_progress' | 'complete'; skill?: string; resource?: LearningResource | null };
export type Roadmap = { id: number; career: string; items: RoadmapItem[] };
export type CareerRole = { id: number; slug: string; name: string; description: string; required_skills: string[] };
export type User = { id: number; email: string; name: string; role: string; profile_complete: boolean };
export type DashboardData = { profile: Profile; recommendations: CareerRecommendation[]; roadmap: Roadmap | null; stats: { career_match: number; skill_match: number; readiness: number; skill_gaps: number }; catalog_size: number };
