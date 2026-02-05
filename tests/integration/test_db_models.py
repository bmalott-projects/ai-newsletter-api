"""Integration tests for database models.

These tests verify:
- Model relationships
- CASCADE delete behavior
- Database constraints (uniqueness, foreign keys)
- Default values
- Data integrity
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.content_item import ContentItem
from app.db.models.interest import Interest
from app.db.models.newsletter import Newsletter
from app.db.models.user import User


def _unique_email() -> str:
    """Generate a unique email for each test."""
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


def _unique_url() -> str:
    """Generate a unique URL for each test."""
    return f"https://example.com/{uuid.uuid4().hex[:8]}"


class TestModelRelationships:
    """Test SQLAlchemy model relationships."""

    @pytest.mark.asyncio
    async def test_user_interests_relationship(self, db_session: AsyncSession) -> None:
        """Test that User.interests returns related Interest objects."""
        # Arrange
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()  # Get user.id

        interest1 = Interest(user_id=user.id, name="Python")
        interest2 = Interest(user_id=user.id, name="FastAPI")
        db_session.add_all([interest1, interest2])
        await db_session.commit()

        # Act
        result = await db_session.execute(
            select(User).where(User.id == user.id).options(selectinload(User.interests))
        )
        user_with_interests = result.scalar_one()

        # Assert
        assert len(user_with_interests.interests) == 2
        assert {i.name for i in user_with_interests.interests} == {"Python", "FastAPI"}
        assert all(i.user_id == user.id for i in user_with_interests.interests)

    @pytest.mark.asyncio
    async def test_user_newsletters_relationship(self, db_session: AsyncSession) -> None:
        """Test that User.newsletters returns related Newsletter objects."""
        # Arrange
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        newsletter1 = Newsletter(user_id=user.id, title="Newsletter 1")
        newsletter2 = Newsletter(user_id=user.id, title="Newsletter 2")
        db_session.add_all([newsletter1, newsletter2])
        await db_session.commit()

        # Act
        result = await db_session.execute(
            select(User).where(User.id == user.id).options(selectinload(User.newsletters))
        )
        user_with_newsletters = result.scalar_one()

        # Assert
        assert len(user_with_newsletters.newsletters) == 2
        assert {n.title for n in user_with_newsletters.newsletters} == {
            "Newsletter 1",
            "Newsletter 2",
        }
        assert all(n.user_id == user.id for n in user_with_newsletters.newsletters)

    @pytest.mark.asyncio
    async def test_newsletter_content_items_relationship(self, db_session: AsyncSession) -> None:
        """Test that Newsletter.content_items returns related ContentItem objects."""
        # Arrange
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        newsletter = Newsletter(user_id=user.id, title="Test Newsletter")
        db_session.add(newsletter)
        await db_session.flush()

        item1 = ContentItem(
            newsletter_id=newsletter.id,
            interest="Python",
            source_url=_unique_url(),
            summary="Summary 1",
        )
        item2 = ContentItem(
            newsletter_id=newsletter.id,
            interest="FastAPI",
            source_url=_unique_url(),
            summary="Summary 2",
        )
        db_session.add_all([item1, item2])
        await db_session.commit()

        # Act
        result = await db_session.execute(
            select(Newsletter)
            .where(Newsletter.id == newsletter.id)
            .options(selectinload(Newsletter.content_items))
        )
        newsletter_with_items = result.scalar_one()

        # Assert
        assert len(newsletter_with_items.content_items) == 2
        assert {item.interest for item in newsletter_with_items.content_items} == {
            "Python",
            "FastAPI",
        }
        assert all(
            item.newsletter_id == newsletter.id for item in newsletter_with_items.content_items
        )

    @pytest.mark.asyncio
    async def test_interest_user_relationship(self, db_session: AsyncSession) -> None:
        """Test that Interest.user returns parent User."""
        # Arrange
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        interest = Interest(user_id=user.id, name="Python")
        db_session.add(interest)
        await db_session.commit()

        # Act
        result = await db_session.execute(
            select(Interest).where(Interest.id == interest.id).options(selectinload(Interest.user))
        )
        interest_with_user = result.scalar_one()

        # Assert
        assert interest_with_user.user is not None
        assert interest_with_user.user.id == user.id
        assert interest_with_user.user.email == user.email

    @pytest.mark.asyncio
    async def test_content_item_newsletter_relationship(self, db_session: AsyncSession) -> None:
        """Test that ContentItem.newsletter returns parent Newsletter."""
        # Arrange
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        newsletter = Newsletter(user_id=user.id, title="Test Newsletter")
        db_session.add(newsletter)
        await db_session.flush()

        content_item = ContentItem(
            newsletter_id=newsletter.id,
            interest="Python",
            source_url=_unique_url(),
            summary="Summary",
        )
        db_session.add(content_item)
        await db_session.commit()

        # Act
        result = await db_session.execute(
            select(ContentItem)
            .where(ContentItem.id == content_item.id)
            .options(selectinload(ContentItem.newsletter))
        )
        content_item_with_newsletter = result.scalar_one()

        # Assert
        assert content_item_with_newsletter.newsletter is not None
        assert content_item_with_newsletter.newsletter.id == newsletter.id
        assert content_item_with_newsletter.newsletter.title == newsletter.title


class TestCascadeDelete:
    """Test CASCADE delete behavior."""

    @pytest.mark.asyncio
    async def test_cascade_delete_user_deletes_interests(self, db_session: AsyncSession) -> None:
        """Test that deleting a user deletes all associated interests."""
        # Arrange
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        interest1 = Interest(user_id=user.id, name="Python")
        interest2 = Interest(user_id=user.id, name="FastAPI")
        db_session.add_all([interest1, interest2])
        await db_session.commit()

        # Verify interests exist
        user_id = user.id
        result = await db_session.execute(select(Interest).where(Interest.user_id == user_id))
        assert len(result.scalars().all()) == 2

        # Act
        # Use execute with delete statement to let database handle CASCADE
        await db_session.execute(delete(User).where(User.id == user_id))
        await db_session.commit()

        # Assert: Interests should be deleted via CASCADE
        result = await db_session.execute(select(Interest).where(Interest.user_id == user_id))
        remaining_interests = result.scalars().all()
        assert len(remaining_interests) == 0

    @pytest.mark.asyncio
    async def test_cascade_delete_user_deletes_newsletters(self, db_session: AsyncSession) -> None:
        """Test that deleting a user deletes all associated newsletters."""
        # Arrange
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        newsletter1 = Newsletter(user_id=user.id, title="Newsletter 1")
        newsletter2 = Newsletter(user_id=user.id, title="Newsletter 2")
        db_session.add_all([newsletter1, newsletter2])
        await db_session.commit()

        # Verify newsletters exist
        user_id = user.id
        result = await db_session.execute(select(Newsletter).where(Newsletter.user_id == user_id))
        assert len(result.scalars().all()) == 2

        # Act
        # Use execute with delete statement to let database handle CASCADE
        await db_session.execute(delete(User).where(User.id == user_id))
        await db_session.commit()

        # Assert
        result = await db_session.execute(select(Newsletter).where(Newsletter.user_id == user_id))
        remaining_newsletters = result.scalars().all()
        assert len(remaining_newsletters) == 0

    @pytest.mark.asyncio
    async def test_cascade_delete_newsletter_deletes_content_items(
        self, db_session: AsyncSession
    ) -> None:
        """Test that deleting a newsletter deletes all associated content items."""
        # Arrange
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        newsletter = Newsletter(user_id=user.id, title="Test Newsletter")
        db_session.add(newsletter)
        await db_session.flush()

        item1 = ContentItem(
            newsletter_id=newsletter.id,
            interest="Python",
            source_url=_unique_url(),
            summary="Summary 1",
        )
        item2 = ContentItem(
            newsletter_id=newsletter.id,
            interest="FastAPI",
            source_url=_unique_url(),
            summary="Summary 2",
        )
        db_session.add_all([item1, item2])
        await db_session.commit()

        # Verify content items exist
        newsletter_id = newsletter.id
        result = await db_session.execute(
            select(ContentItem).where(ContentItem.newsletter_id == newsletter_id)
        )
        assert len(result.scalars().all()) == 2

        # Act
        # Use execute with delete statement to let database handle CASCADE
        await db_session.execute(delete(Newsletter).where(Newsletter.id == newsletter_id))
        await db_session.commit()

        # Assert
        result = await db_session.execute(
            select(ContentItem).where(ContentItem.newsletter_id == newsletter_id)
        )
        remaining_items = result.scalars().all()
        assert len(remaining_items) == 0


class TestConstraints:
    """Test database constraints."""

    @pytest.mark.asyncio
    async def test_user_email_uniqueness_constraint(self, db_session: AsyncSession) -> None:
        """Test that User model enforces unique email constraint."""
        # Arrange
        user1 = User(email=_unique_email(), hashed_password="hashed1")
        db_session.add(user1)
        await db_session.commit()
        user1_email = user1.email

        # Act
        user2 = User(email=user1_email, hashed_password="hashed2")
        db_session.add(user2)

        # Assert
        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_content_item_source_url_uniqueness_constraint(
        self, db_session: AsyncSession
    ) -> None:
        """Test that ContentItem model enforces unique source_url constraint."""
        # Arrange
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        newsletter = Newsletter(user_id=user.id, title="Test Newsletter")
        db_session.add(newsletter)
        await db_session.flush()

        # Create first content item
        shared_url = _unique_url()
        item1 = ContentItem(
            newsletter_id=newsletter.id,
            interest="Python",
            source_url=shared_url,
            summary="Summary 1",
        )
        db_session.add(item1)
        await db_session.commit()

        # Act
        item2 = ContentItem(
            newsletter_id=newsletter.id,
            interest="FastAPI",
            source_url=shared_url,  # Same URL
            summary="Summary 2",
        )
        db_session.add(item2)

        # Assert
        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_interest_requires_valid_user_id(self, db_session: AsyncSession) -> None:
        """Test that Interest model enforces foreign key constraint on user_id."""
        # Arrange
        interest = Interest(user_id=99999, name="Python")  # Non-existent user_id
        db_session.add(interest)

        # Act & Assert: Should raise IntegrityError
        with pytest.raises(IntegrityError):
            await db_session.commit()

        # Rollback for cleanup
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_newsletter_requires_valid_user_id(self, db_session: AsyncSession) -> None:
        """Test that Newsletter model enforces foreign key constraint on user_id."""
        # Arrange
        newsletter = Newsletter(user_id=99999, title="Test Newsletter")
        db_session.add(newsletter)

        # Act
        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_content_item_requires_valid_newsletter_id(
        self, db_session: AsyncSession
    ) -> None:
        """Test that ContentItem model enforces foreign key constraint on newsletter_id."""
        # Arrange: Create content item with invalid newsletter_id
        item = ContentItem(
            newsletter_id=99999,  # Non-existent newsletter_id
            interest="Python",
            source_url=_unique_url(),
            summary="Summary",
        )
        db_session.add(item)

        # Act & Assert: Should raise IntegrityError
        with pytest.raises(IntegrityError):
            await db_session.commit()

        # Rollback for cleanup
        await db_session.rollback()


class TestDefaultValues:
    """Test default values for model fields."""

    @pytest.mark.asyncio
    async def test_interest_active_default_true(self, db_session: AsyncSession) -> None:
        """Test that new Interest has active=True by default."""
        # Arrange
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        # Act
        interest = Interest(user_id=user.id, name="Python")
        db_session.add(interest)
        await db_session.commit()

        # Assert
        assert interest.active is True

    @pytest.mark.asyncio
    async def test_user_created_at_auto_populated(self, db_session: AsyncSession) -> None:
        """Test that User.created_at is auto-populated."""
        # Arrange
        before_creation = datetime.now(UTC)

        # Act
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.commit()
        after_creation = datetime.now(UTC)

        # Assert
        assert user.created_at is not None
        # created_at is timezone-aware, compare with UTC (allow 1 second tolerance)
        time_diff_before = (user.created_at - before_creation).total_seconds()
        time_diff_after = (after_creation - user.created_at).total_seconds()
        assert -1 <= time_diff_before <= 5  # Allow some tolerance
        assert -1 <= time_diff_after <= 5

    @pytest.mark.asyncio
    async def test_newsletter_created_at_auto_populated(self, db_session: AsyncSession) -> None:
        """Test that Newsletter.created_at is auto-populated."""
        # Arrange: Create user
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        # Act
        before_creation = datetime.now(UTC)
        newsletter = Newsletter(user_id=user.id, title="Test Newsletter")
        db_session.add(newsletter)
        await db_session.commit()
        after_creation = datetime.now(UTC)

        # Assert
        assert newsletter.created_at is not None
        # created_at is timezone-aware, compare with UTC (allow 1 second tolerance)
        time_diff_before = (newsletter.created_at - before_creation).total_seconds()
        time_diff_after = (after_creation - newsletter.created_at).total_seconds()
        assert -1 <= time_diff_before <= 5  # Allow some tolerance
        assert -1 <= time_diff_after <= 5


class TestDataIntegrity:
    """Test data integrity and multiple relationships."""

    @pytest.mark.asyncio
    async def test_user_can_have_multiple_interests(self, db_session: AsyncSession) -> None:
        """Test that a user can have many interests."""
        # Arrange: Create user
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        # Act
        interests = [Interest(user_id=user.id, name=f"Interest {i}") for i in range(2)]
        db_session.add_all(interests)
        await db_session.commit()

        # Assert
        result = await db_session.execute(select(Interest).where(Interest.user_id == user.id))
        user_interests = result.scalars().all()
        assert len(user_interests) == 2

    @pytest.mark.asyncio
    async def test_user_can_have_multiple_newsletters(self, db_session: AsyncSession) -> None:
        """Test that a user can have many newsletters."""
        # Arrange: Create user
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        # Act
        newsletters = [Newsletter(user_id=user.id, title=f"Newsletter {i}") for i in range(2)]
        db_session.add_all(newsletters)
        await db_session.commit()

        # Assert
        result = await db_session.execute(select(Newsletter).where(Newsletter.user_id == user.id))
        user_newsletters = result.scalars().all()
        assert len(user_newsletters) == 2

    @pytest.mark.asyncio
    async def test_newsletter_can_have_multiple_content_items(
        self, db_session: AsyncSession
    ) -> None:
        """Test that a newsletter can have many content items."""
        # Arrange
        user = User(email=_unique_email(), hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        newsletter = Newsletter(user_id=user.id, title="Test Newsletter")
        db_session.add(newsletter)
        await db_session.flush()

        # Act
        items = [
            ContentItem(
                newsletter_id=newsletter.id,
                interest=f"Interest {i}",
                source_url=_unique_url(),
                summary=f"Summary {i}",
            )
            for i in range(2)
        ]
        db_session.add_all(items)
        await db_session.commit()

        # Assert
        result = await db_session.execute(
            select(ContentItem).where(ContentItem.newsletter_id == newsletter.id)
        )
        newsletter_items = result.scalars().all()
        assert len(newsletter_items) == 2
