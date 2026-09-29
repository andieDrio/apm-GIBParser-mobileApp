from app.domain.assessment import AssessmentResult
from app.db.models import AssessmentModel


def save_assessment(db, result: AssessmentResult) -> AssessmentModel:
    fields = result.json_fields()
    model = AssessmentModel(
        assessment_id=result.assessment_id,
        run_id=result.run_id,
        activity_level=result.activity_level.value,
        confidence=result.confidence.value,
        facts_json=fields["facts"],
        observations_json=fields["observations"],
        assessment=result.assessment,
        recommended_attention_json=fields["recommended_attention"],
        basis_json=fields["basis"],
    )
    db.add(model)
    db.flush()
    return model
