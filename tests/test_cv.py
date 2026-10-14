"""
Unit tests for Computer Vision portion estimation and nutrition scaling.
"""

from app.cv.inference import (
    NutritionInfo,
    estimate_portion_from_bbox,
    scale_nutrition,
)


def test_estimate_portion_from_bbox_brackets():
    img_w, img_h = 1000, 1000  # Total area = 1,000,000 px

    # Tiny box: 100 x 100 = 10,000 px (1% of image -> relative area 0.01 <= 0.03) -> 50g
    tiny_bbox = [100, 100, 200, 200]
    assert estimate_portion_from_bbox(tiny_bbox, img_w, img_h) == 50.0

    # Small box: 250 x 250 = 62,500 px (6.25% of image <= 0.08) -> 100g
    small_bbox = [100, 100, 350, 350]
    assert estimate_portion_from_bbox(small_bbox, img_w, img_h) == 100.0

    # Medium box: 350 x 350 = 122,500 px (12.25% of image <= 0.18) -> 175g
    med_bbox = [100, 100, 450, 450]
    assert estimate_portion_from_bbox(med_bbox, img_w, img_h) == 175.0

    # Large box: 500 x 500 = 250,000 px (25% of image <= 0.35) -> 250g
    large_bbox = [100, 100, 600, 600]
    assert estimate_portion_from_bbox(large_bbox, img_w, img_h) == 250.0

    # Huge box: 800 x 800 = 640,000 px (64% of image <= 1.0) -> 350g
    huge_bbox = [100, 100, 900, 900]
    assert estimate_portion_from_bbox(huge_bbox, img_w, img_h) == 350.0


def test_estimate_portion_fallback():
    # Degenerate bbox or dimensions fallback to default_portion_g
    assert estimate_portion_from_bbox([], 100, 100, default_portion_g=150.0) == 150.0
    assert estimate_portion_from_bbox([0, 0, 10, 10], 0, 100, default_portion_g=150.0) == 150.0


def test_scale_nutrition():
    # Chicken breast nutrition per 100g: 165 kcal, 31g protein, 3.6g fat, 0g carbs
    chicken = NutritionInfo(
        food_item_id=1,
        name="Chicken Breast",
        calories_per_100g=165.0,
        protein_per_100g=31.0,
        fat_per_100g=3.6,
        carbs_per_100g=0.0,
    )

    # For 200g portion -> factor 2.0
    scaled = scale_nutrition(chicken, portion_g=200.0)
    assert scaled["calories"] == 330.0
    assert scaled["protein_g"] == 62.0
    assert scaled["fat_g"] == 7.2
    assert scaled["carbs_g"] == 0.0

    # For 50g portion -> factor 0.5
    scaled_half = scale_nutrition(chicken, portion_g=50.0)
    assert scaled_half["calories"] == 82.5
    assert scaled_half["protein_g"] == 15.5
    assert scaled_half["fat_g"] == 1.8
    assert scaled_half["carbs_g"] == 0.0


def test_pizza_geometric_portion_diameter():
    from app.cv.inference import estimate_portion_with_geometry

    # Simulated 500x500 image with a whole 450x450 pizza (spans ~90% of frame, ~12 inch pan)
    pizza_bbox = [25, 25, 475, 475]
    grams, meta = estimate_portion_with_geometry(pizza_bbox, 500, 500, food_class="pizza")

    assert grams >= 500.0  # Whole pizza should weigh between 500g and 900g
    assert grams <= 950.0
    assert meta is not None
    assert "Diameter" in meta
    assert "Cylindrical Slab" in meta


def test_suppress_and_merge_overlapping_boxes():
    from app.cv.inference import _suppress_and_merge_overlapping_boxes, NutritionInfo

    pizza_info = NutritionInfo(name="Pizza", calories_per_100g=266.0)

    # Simulate: 1 large whole pizza box + 2 smaller slice boxes inside it
    candidates = [
        {"class_name": "pizza", "confidence": 0.71, "bbox": [50, 50, 480, 480], "info": pizza_info},
        {"class_name": "pizza", "confidence": 0.73, "bbox": [60, 60, 260, 260], "info": pizza_info},
        {"class_name": "pizza", "confidence": 0.54, "bbox": [50, 250, 480, 480], "info": pizza_info},
    ]

    filtered = _suppress_and_merge_overlapping_boxes(candidates)
    # The 2 smaller sub-boxes inside the whole pizza must be suppressed into 1 single whole pizza!
    assert len(filtered) == 1
    assert filtered[0]["confidence"] == 0.73  # Inherited max confidence
    assert filtered[0]["bbox"] == [50, 50, 480, 480]


def test_non_food_objects_excluded():
    from app.cv.inference import NON_FOOD_EXCLUDE

    assert "dining table" in NON_FOOD_EXCLUDE
    assert "knife" in NON_FOOD_EXCLUDE
    assert "water bottle" in NON_FOOD_EXCLUDE
    assert "fork" in NON_FOOD_EXCLUDE
    assert "pizza" not in NON_FOOD_EXCLUDE


def test_parse_gemini_response_with_macros():
    from app.cv.gemini_vision import _parse_gemini_response

    sample_json = """
    ```json
    [
      {
        "food_name": "Masala Dosa",
        "estimated_grams": 180,
        "confidence": 0.96,
        "calories": 330,
        "protein_g": 6.5,
        "fat_g": 9.0,
        "carbs_g": 52.0
      },
      {
        "food_name": "Coconut Chutney",
        "estimated_grams": 40,
        "confidence": 0.93,
        "calories": 95,
        "protein_g": 1.1,
        "fat_g": 9.2,
        "carbs_g": 2.8
      }
    ]
    ```
    """
    results = _parse_gemini_response(sample_json)
    assert len(results) == 2
    assert results[0].food_name == "Masala Dosa"
    assert results[0].estimated_grams == 180.0
    assert results[0].calories == 330.0
    assert results[0].protein_g == 6.5
    assert results[1].food_name == "Coconut Chutney"
    assert results[1].fat_g == 9.2

