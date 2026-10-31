"""Import every model so Base.metadata knows the full schema."""
from app.models.base import Base  # noqa: F401
from app.models.interview import InterviewAttempt, InterviewQuestion  # noqa: F401
from app.models.jobs import Application, Job, JobSkill  # noqa: F401
from app.models.learning import (  # noqa: F401
    LearningResource,
    Project,
    ProjectSkill,
    ResourceSkill,
    Roadmap,
    RoadmapItem,
    SkillRecallSchedule,
    UserProgress,
    UserProject,
    YoutubeResource,
)
from app.models.ml import Recommendation, SearchHistory, SkillEmbedding, UserActivity, UserEmbedding  # noqa: F401
from app.models.resume import Resume, ResumeSkill  # noqa: F401
from app.models.skills import Role, RoleSkill, Skill, SkillAlias, SkillDependency, SkillTaxonomy  # noqa: F401
from app.models.user import Profile, RevokedToken, User  # noqa: F401
from app.models.user_skills import Certification, Evidence, UserSkill, UserSkillAssessment  # noqa: F401
