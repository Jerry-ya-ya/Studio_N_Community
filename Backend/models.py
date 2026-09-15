# models.py
# 定義資料庫模型
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from time_utils import taipei_now, to_taipei_iso
from role_groups import DEFAULT_ROLE

date_format = taipei_now()

db = SQLAlchemy()

# 關聯表：表示誰加了誰
friend_association = Table(
    'friend_association',
    db.Model.metadata,
    Column('user_id', Integer, ForeignKey('user.id')),
    Column('friend_id', Integer, ForeignKey('user.id'))
)

# 定義使用者模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now()) # 註冊時間

    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    avatar_url = db.Column(db.String(255))
    avatar_source = db.Column(db.String(20), default='github', nullable=False)
    nickname = db.Column(db.String(80))
    github_url = db.Column(db.String(255))
    capability_direction = db.Column(db.String(32), default='both', nullable=False)
    capability_stack = db.Column(db.String(32), default='fullstack', nullable=False)
    capability_focus = db.Column(db.String(32), default='game-systems', nullable=False)
    capability_style = db.Column(db.String(32), default='professional', nullable=False)
    role = db.Column(db.String(20), default=DEFAULT_ROLE)
    experience = db.Column(db.Integer, default=0, nullable=False)
    review_experience = db.Column(db.Integer, default=0, nullable=False)
    pm_experience = db.Column(db.Integer, default=0, nullable=False)

    email = db.Column(db.String(120), unique=True)
    email_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime)
    
    todos = db.relationship('Todo', foreign_keys='Todo.user_id', backref='user', lazy=True) # 一對多關聯

    friends = relationship(
        'User',
        secondary=friend_association,
        primaryjoin=id == friend_association.c.user_id,
        secondaryjoin=id == friend_association.c.friend_id,
        backref='added_by'  # 可以反查「被誰加為好友」
    )

    @property
    def display_username(self):
        return '已刪除' if self.is_deleted else self.username

    @property
    def display_email(self):
        return '已刪除' if self.is_deleted else self.email

    @property
    def display_nickname(self):
        return '已刪除' if self.is_deleted else self.nickname

    def to_dict(self, include_sensitive=False):
        data = {
            'id': self.id,
            'username': self.display_username,
            'nickname': self.display_nickname,
            'github_url': self.github_url,
            'githubUrl': self.github_url,
            'capability_direction': self.capability_direction,
            'capabilityDirection': self.capability_direction,
            'capability_stack': self.capability_stack,
            'capabilityStack': self.capability_stack,
            'capability_focus': self.capability_focus,
            'capabilityFocus': self.capability_focus,
            'capability_style': self.capability_style,
            'capabilityStyle': self.capability_style,
            'role': self.role,
            'experience': self.experience,
            'review_experience': self.review_experience,
            'pm_experience': self.pm_experience,
            'is_active': self.is_active,
            'isActive': self.is_active,
            'is_deleted': self.is_deleted,
            'avatar_url': self.avatar_url,
            'avatar_source': self.avatar_source,
            'avatarSource': self.avatar_source,
            'created_at': to_taipei_iso(self.created_at)
        }
        if include_sensitive:
            data['email'] = self.display_email
            data['email_verified'] = self.email_verified
        return data


class RefreshToken(db.Model):
    """Server-side state for a rotating refresh-token family."""
    __table_args__ = (
        db.Index('ix_refresh_token_family_revoked', 'family_id', 'revoked_at'),
    )

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, nullable=False, index=True)
    family_id = db.Column(db.String(36), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=taipei_now, nullable=False)
    revoked_at = db.Column(db.DateTime)
    replaced_by_jti = db.Column(db.String(36))

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    user = db.relationship(
        'User',
        backref=db.backref('refresh_tokens', cascade='all, delete-orphan'),
    )

class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=taipei_now)

    from_user = db.relationship('User', foreign_keys=[from_user_id], backref='sent_requests')
    to_user = db.relationship('User', foreign_keys=[to_user_id], backref='received_requests')

# 定義 Todo 模型
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, default=False)
    settled = db.Column(db.Boolean, default=False, nullable=False)
    priority = db.Column(db.Integer, default=5, nullable=False)
    difficulty = db.Column(db.Integer, default=5, nullable=False)
    duration = db.Column(db.Integer, default=5, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) # 將來可用來綁定使用者
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    claimed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project_recruitment.id'))
    created_at = db.Column(db.DateTime, default=taipei_now)

    creator = db.relationship('User', foreign_keys=[created_by_id], backref='created_todos')
    claimed_by = db.relationship('User', foreign_keys=[claimed_by_id], backref='claimed_todos')
    project = db.relationship('ProjectRecruitment', backref='todos')

# 定義新聞模型
class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=taipei_now)

class HomeNewsItem(db.Model):
    __table_args__ = (
        db.CheckConstraint("theme IN ('cmen', 'eden')", name='ck_home_news_theme'),
    )

    id = db.Column(db.Integer, primary_key=True)
    theme = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    tag = db.Column(db.String(40), nullable=False)
    background_url = db.Column(db.String(255))
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=taipei_now)
    updated_at = db.Column(db.DateTime, default=taipei_now, onupdate=taipei_now)

class MemberContentItem(db.Model):
    __table_args__ = (
        db.CheckConstraint("role IN ('superadmin', 'admin', 'member', 'user')", name='ck_member_content_role'),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    github_url = db.Column(db.String(255), nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=taipei_now)
    updated_at = db.Column(db.DateTime, default=taipei_now, onupdate=taipei_now)

class ScheduleState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(50), unique=True, nullable=False)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)

class UserSchedule(db.Model):
    __table_args__ = (
        db.UniqueConstraint('user_id', name='uq_user_schedule_user_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    blocks = db.Column(db.JSON, default=list, nullable=False)
    created_at = db.Column(db.DateTime, default=taipei_now)
    updated_at = db.Column(db.DateTime, default=taipei_now, onupdate=taipei_now)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('schedule', uselist=False))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=taipei_now)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='posts')

class PostLike(db.Model):
    __table_args__ = (
        db.UniqueConstraint('post_id', 'user_id', name='uq_post_like_post_user'),
    )

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=taipei_now)

    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    post = db.relationship('Post', backref=db.backref('likes', cascade='all, delete-orphan'))
    user = db.relationship('User', backref='post_likes')

class ProjectRecruitment(db.Model):
    __table_args__ = (
        db.CheckConstraint(
            "review_status IN ('open', 'pending', 'approved', 'rejected')",
            name='ck_project_recruitment_review_status'
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    role_needed = db.Column(db.String(120))
    contact = db.Column(db.String(160))
    github_url = db.Column(db.String(2048))
    max_members = db.Column(db.Integer)
    token_budget = db.Column(db.Integer, default=100, nullable=False)
    token_used = db.Column(db.Integer, default=0, nullable=False)
    level = db.Column(db.Integer, default=1, nullable=False)
    review_status = db.Column(db.String(20), default='open', nullable=False)
    created_at = db.Column(db.DateTime, default=taipei_now)

    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator = db.relationship('User', backref='project_recruitments')
    members = db.relationship(
        'ProjectRecruitmentMember',
        back_populates='project',
        cascade='all, delete-orphan'
    )

class ProjectRecruitmentMember(db.Model):
    __table_args__ = (
        db.UniqueConstraint('project_id', 'user_id', name='uq_project_recruitment_member'),
    )

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=taipei_now)

    project_id = db.Column(db.Integer, db.ForeignKey('project_recruitment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    project = db.relationship('ProjectRecruitment', back_populates='members')
    user = db.relationship('User', backref='project_recruitment_memberships')

class DailyCheckIn(db.Model):
    __table_args__ = (
        db.UniqueConstraint('user_id', 'checkin_date', name='uq_daily_check_in_user_date'),
    )

    id = db.Column(db.Integer, primary_key=True)
    checkin_date = db.Column(db.Date, nullable=False)
    points = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=taipei_now)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='daily_check_ins')


class UserAchievement(db.Model):
    """An immutable record that a server-verified achievement was unlocked."""
    __table_args__ = (
        db.UniqueConstraint('user_id', 'achievement_key', name='uq_user_achievement_key'),
    )

    id = db.Column(db.Integer, primary_key=True)
    achievement_key = db.Column(db.String(50), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=taipei_now, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    user = db.relationship(
        'User',
        backref=db.backref('unlocked_achievements', cascade='all, delete-orphan'),
    )

class ActivityPromotion(db.Model):
    __table_args__ = (
        db.CheckConstraint("visibility IN ('public', 'private')", name='ck_activity_promotion_visibility'),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    visibility = db.Column(db.String(20), default='private', nullable=False, index=True)
    target_filter = db.Column(db.String(160), default='all', nullable=False)
    image_url = db.Column(db.String(255))
    start_at = db.Column(db.DateTime)
    end_at = db.Column(db.DateTime)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=taipei_now)
    updated_at = db.Column(db.DateTime, default=taipei_now, onupdate=taipei_now)

    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', backref='activity_promotions')


class FormTemplate(db.Model):
    """An admin-managed form whose constrained definition is stored as JSONB."""
    __tablename__ = 'form_template'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    definition = db.Column(
        JSONB().with_variant(db.JSON(), 'sqlite'),
        nullable=False,
        default=lambda: {'schemaVersion': 1, 'questions': []},
    )
    version = db.Column(db.Integer, nullable=False, default=1)
    settlement_at = db.Column(db.DateTime, index=True)
    settled_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=taipei_now, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=taipei_now,
        onupdate=taipei_now,
        nullable=False,
    )

    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='SET NULL'),
        index=True,
    )
    created_by = db.relationship('User', backref='form_templates')


class FormSubmission(db.Model):
    """An immutable user's answers to one published form version."""
    __tablename__ = 'form_submission'
    __table_args__ = (
        db.UniqueConstraint(
            'form_id', 'user_id', 'form_version',
            name='uq_form_submission_form_user_version',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    form_version = db.Column(db.Integer, nullable=False)
    form_snapshot = db.Column(
        JSONB().with_variant(db.JSON(), 'sqlite'), nullable=False
    )
    answers = db.Column(
        JSONB().with_variant(db.JSON(), 'sqlite'), nullable=False
    )
    submitted_at = db.Column(db.DateTime, default=taipei_now, nullable=False)

    form_id = db.Column(
        db.Integer,
        db.ForeignKey('form_template.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    form = db.relationship(
        'FormTemplate',
        backref=db.backref('submissions', cascade='all, delete-orphan'),
    )
    user = db.relationship(
        'User',
        backref=db.backref('form_submissions', cascade='all, delete-orphan'),
    )


def load_models():
    """Keep all table models registered from one place before schema creation."""
    return (
        User,
        RefreshToken,
        FriendRequest,
        Todo,
        News,
        HomeNewsItem,
        MemberContentItem,
        ScheduleState,
        UserSchedule,
        Post,
        PostLike,
        ProjectRecruitment,
        ProjectRecruitmentMember,
        DailyCheckIn,
        UserAchievement,
        ActivityPromotion,
        FormTemplate,
        FormSubmission,
    )
