"""Dataset publication and active restaurant queries."""

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session, selectinload

from restaurant_recommender.domain.models import CanonicalRestaurant, DatasetStatus
from restaurant_recommender.domain.normalization import comparison_text
from restaurant_recommender.domain.recommendations import (
    BudgetRange,
    Candidate,
    RecommendationQuery,
)
from restaurant_recommender.ingestion.contracts import SourceMetadata
from restaurant_recommender.persistence.models import (
    BudgetProfileRow,
    DatasetVersionRow,
    RecommendationAuditRow,
    RestaurantCuisineRow,
    RestaurantRow,
)


class DatasetRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_idempotent(self, metadata: SourceMetadata) -> DatasetVersionRow | None:
        return self.session.scalar(
            select(DatasetVersionRow).where(
                DatasetVersionRow.source_name == metadata.name,
                DatasetVersionRow.source_revision == metadata.revision,
                DatasetVersionRow.content_hash == metadata.content_hash,
            )
        )

    def create_staging(self, metadata: SourceMetadata) -> DatasetVersionRow:
        version = DatasetVersionRow(
            source_name=metadata.name,
            source_revision=metadata.revision,
            source_split=metadata.split,
            source_schema={"columns": list(metadata.schema)},
            schema_version="1",
            content_hash=metadata.content_hash,
            status=DatasetStatus.STAGING.value,
            quality_report={},
        )
        self.session.add(version)
        self.session.flush()
        return version

    def load_restaurants(
        self, version: DatasetVersionRow, restaurants: Iterable[CanonicalRestaurant]
    ) -> None:
        if version.status != DatasetStatus.STAGING.value:
            raise ValueError("only staging versions can receive records")
        for restaurant in restaurants:
            row = RestaurantRow(
                id=uuid.uuid4(),
                dataset_version_id=version.id,
                source_key=restaurant.source_key,
                name=restaurant.name,
                name_normalized=restaurant.name_normalized,
                city=restaurant.city,
                city_normalized=restaurant.city_normalized,
                locality=restaurant.locality,
                locality_normalized=restaurant.locality_normalized,
                address=restaurant.address,
                average_cost_minor=restaurant.cost.minor_units if restaurant.cost else None,
                currency_code=restaurant.cost.currency_code if restaurant.cost else None,
                cost_basis=restaurant.cost.basis if restaurant.cost else None,
                rating=restaurant.rating.value if restaurant.rating else None,
                rating_scale=restaurant.rating.scale if restaurant.rating else 5,
                votes=restaurant.votes,
                attributes=restaurant.attributes,
                source_url=restaurant.source_url,
                source_payload_hash=restaurant.source_payload_hash,
            )
            row.cuisines = [
                RestaurantCuisineRow(
                    cuisine=value, cuisine_normalized=comparison_text(value) or value
                )
                for value in restaurant.cuisines
            ]
            self.session.add(row)
        self.session.flush()

    def validate(self, version: DatasetVersionRow, report: dict[str, object]) -> None:
        if version.status != DatasetStatus.STAGING.value:
            raise ValueError("only staging versions can be validated")
        count = self.session.scalar(
            select(func.count())
            .select_from(RestaurantRow)
            .where(RestaurantRow.dataset_version_id == version.id)
        )
        if count != report["accepted_rows"]:
            raise ValueError("database record count does not match quality report")
        version.record_count = int(count or 0)
        version.rejected_count = _report_int(report, "rejected_rows")
        version.quality_report = report
        version.status = DatasetStatus.VALIDATED.value
        self.session.flush()

    def fail(self, version: DatasetVersionRow, report: dict[str, object]) -> None:
        if version.status == DatasetStatus.ACTIVE.value:
            raise ValueError("an active version cannot be marked failed")
        version.status = DatasetStatus.FAILED.value
        version.quality_report = report
        version.rejected_count = _report_int(report, "rejected_rows")
        self.session.flush()

    def activate(self, version_id: uuid.UUID) -> DatasetVersionRow:
        # The row lock serializes publishers; the partial unique index is a final guard.
        versions = self.session.scalars(
            select(DatasetVersionRow)
            .where(
                DatasetVersionRow.status.in_(
                    [DatasetStatus.ACTIVE.value, DatasetStatus.VALIDATED.value]
                )
            )
            .with_for_update()
        ).all()
        target = next((item for item in versions if item.id == version_id), None)
        if target is None or target.status not in {
            DatasetStatus.VALIDATED.value,
            DatasetStatus.ACTIVE.value,
            DatasetStatus.RETIRED.value,
        }:
            # Retired is loaded separately for rollback.
            target = self.session.get(DatasetVersionRow, version_id, with_for_update=True)
        if target is None or target.status not in {
            DatasetStatus.VALIDATED.value,
            DatasetStatus.ACTIVE.value,
            DatasetStatus.RETIRED.value,
        }:
            raise ValueError("only validated, active, or retired versions can be activated")
        for item in versions:
            if item.status == DatasetStatus.ACTIVE.value and item.id != target.id:
                item.status = DatasetStatus.RETIRED.value
        # Release the partial unique index before promoting the replacement.
        self.session.flush()
        target.status = DatasetStatus.ACTIVE.value
        target.activated_at = datetime.now(UTC)
        self.session.flush()
        return target

    def list_versions(self) -> list[DatasetVersionRow]:
        return list(
            self.session.scalars(
                select(DatasetVersionRow).order_by(DatasetVersionRow.created_at.desc())
            )
        )

    def get_version(self, version_id: uuid.UUID) -> DatasetVersionRow | None:
        return self.session.get(DatasetVersionRow, version_id)


class RestaurantRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def active(self, *, limit: int = 100) -> list[RestaurantRow]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        statement = (
            select(RestaurantRow)
            .join(DatasetVersionRow)
            .where(DatasetVersionRow.status == DatasetStatus.ACTIVE.value)
            .options(selectinload(RestaurantRow.cuisines))
            .order_by(RestaurantRow.name_normalized, RestaurantRow.source_key)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def active_version(self) -> DatasetVersionRow | None:
        return self.session.scalar(
            select(DatasetVersionRow).where(DatasetVersionRow.status == DatasetStatus.ACTIVE.value)
        )

    def resolve_budget(self, tier: str, currency_code: str) -> tuple[BudgetRange, int] | None:
        row = self.session.scalar(
            select(BudgetProfileRow)
            .where(
                BudgetProfileRow.key == tier,
                BudgetProfileRow.currency_code == currency_code,
            )
            .order_by(BudgetProfileRow.version.desc())
            .limit(1)
        )
        if row is None:
            return None
        return BudgetRange(
            row.minimum_minor, row.maximum_minor, row.currency_code, row.key
        ), row.version

    def active_rating_scale(self) -> Decimal | None:
        return self.session.scalar(
            select(func.max(RestaurantRow.rating_scale))
            .join(DatasetVersionRow)
            .where(DatasetVersionRow.status == DatasetStatus.ACTIVE.value)
        )

    def filter_candidates(
        self,
        query: RecommendationQuery,
        *,
        limit: int,
        relax: str | None = None,
    ) -> list[Candidate]:
        if not 1 <= limit <= 5000:
            raise ValueError("limit must be between 1 and 5000")
        statement = (
            select(RestaurantRow)
            .join(DatasetVersionRow)
            .where(*_filter_predicates(query, relax))
            .options(selectinload(RestaurantRow.cuisines))
        )
        statement = statement.order_by(
            RestaurantRow.rating.desc().nullslast(),
            RestaurantRow.votes.desc().nullslast(),
            RestaurantRow.name_normalized,
            RestaurantRow.source_key,
        ).limit(limit)
        return [_candidate(row) for row in self.session.scalars(statement).unique()]

    def count_candidates(self, query: RecommendationQuery, *, relax: str) -> int:
        count = self.session.scalar(
            select(func.count())
            .select_from(RestaurantRow)
            .join(DatasetVersionRow)
            .where(*_filter_predicates(query, relax))
        )
        return int(count or 0)

    def locations(self, query: str | None, *, limit: int) -> list[str]:
        statement = (
            select(distinct(RestaurantRow.locality))
            .join(DatasetVersionRow)
            .where(
                DatasetVersionRow.status == DatasetStatus.ACTIVE.value,
                RestaurantRow.locality.is_not(None),
            )
            .order_by(RestaurantRow.locality)
            .limit(limit)
        )
        if query:
            escaped = _like_value(query)
            statement = statement.where(
                RestaurantRow.locality_normalized.ilike(f"%{escaped}%", escape="\\")
            )
        return [value for value in self.session.scalars(statement) if value is not None]

    def cuisines(self, query: str | None, *, limit: int) -> list[str]:
        statement = (
            select(distinct(RestaurantCuisineRow.cuisine))
            .join(RestaurantRow)
            .join(DatasetVersionRow)
            .where(DatasetVersionRow.status == DatasetStatus.ACTIVE.value)
            .order_by(RestaurantCuisineRow.cuisine)
            .limit(limit)
        )
        if query:
            escaped = _like_value(query)
            statement = statement.where(
                RestaurantCuisineRow.cuisine_normalized.ilike(f"%{escaped}%", escape="\\")
            )
        return list(self.session.scalars(statement))

    def budgets(self, currency_code: str) -> list[BudgetProfileRow]:
        latest = (
            select(BudgetProfileRow.key, func.max(BudgetProfileRow.version).label("version"))
            .where(BudgetProfileRow.currency_code == currency_code)
            .group_by(BudgetProfileRow.key)
            .subquery()
        )
        return list(
            self.session.scalars(
                select(BudgetProfileRow)
                .join(
                    latest,
                    (BudgetProfileRow.key == latest.c.key)
                    & (BudgetProfileRow.version == latest.c.version),
                )
                .where(BudgetProfileRow.currency_code == currency_code)
                .order_by(BudgetProfileRow.minimum_minor)
            )
        )

    def record_audit(self, **values: Any) -> None:
        self.session.add(RecommendationAuditRow(**values))
        self.session.commit()


def _report_int(report: dict[str, object], key: str) -> int:
    value = report.get(key, 0)
    if not isinstance(value, int):
        raise TypeError(f"quality report field {key} must be an integer")
    return value


def _candidate(row: RestaurantRow) -> Candidate:
    return Candidate(
        id=row.id,
        source_key=row.source_key,
        name=row.name,
        city=row.city,
        city_normalized=row.city_normalized,
        locality=row.locality,
        locality_normalized=row.locality_normalized,
        cuisines=tuple(item.cuisine for item in row.cuisines),
        cuisines_normalized=tuple(item.cuisine_normalized for item in row.cuisines),
        cost_minor=row.average_cost_minor,
        currency_code=row.currency_code,
        rating=row.rating,
        rating_scale=row.rating_scale,
        votes=row.votes,
        source_url=row.source_url,
    )


def _filter_predicates(query: RecommendationQuery, relax: str | None) -> list[Any]:
    predicates: list[Any] = [
        DatasetVersionRow.status == DatasetStatus.ACTIVE.value,
        RestaurantRow.city_normalized == query.city,
    ]
    if query.locality is not None and relax != "locality":
        predicates.append(RestaurantRow.locality_normalized == query.locality)
    if query.budget is not None and relax != "budget":
        predicates.extend(
            [
                RestaurantRow.currency_code == query.budget.currency_code,
                RestaurantRow.average_cost_minor.is_not(None),
                RestaurantRow.average_cost_minor >= query.budget.minimum_minor,
            ]
        )
        if query.budget.maximum_minor is not None:
            predicates.append(RestaurantRow.average_cost_minor <= query.budget.maximum_minor)
    if query.minimum_rating is not None and relax != "rating":
        predicates.extend(
            [RestaurantRow.rating.is_not(None), RestaurantRow.rating >= query.minimum_rating]
        )
    if query.cuisines and relax != "cuisine":
        predicates.append(
            RestaurantRow.cuisines.any(RestaurantCuisineRow.cuisine_normalized.in_(query.cuisines))
        )
    return predicates


def _like_value(value: str) -> str:
    normalized = comparison_text(value) or ""
    return normalized.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
