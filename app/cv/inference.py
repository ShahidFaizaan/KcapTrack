
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

_model: Optional[Any] = None


def get_model():
    global _model
    if _model is None:
        try:
            from ultralytics import YOLO
        except ImportError as e:
            raise ImportError(
                "Ultralytics is required. Install with: pip install ultralytics"
            ) from e

        try:
            from app.core.config import get_settings
            weights = Path(get_settings().YOLO_WEIGHTS_PATH)
        except Exception:
            weights = Path("models/yolov8n.pt")

        logger.info("Loading YOLO model from %s", weights)
        _model = YOLO(str(weights))
        logger.info("YOLO model loaded (%s classes).", len(_model.names))
    return _model



@dataclass
class NutritionInfo:
    """Nutrition values for a food class (per 100 g)."""
    food_item_id: Optional[int] = None
    name: str = "unknown"
    calories_per_100g: float = 0.0
    protein_per_100g: float = 0.0
    fat_per_100g: float = 0.0
    carbs_per_100g: float = 0.0
    default_portion_g: float = 150.0


@dataclass
class DetectionResult:
    detected_class: str
    confidence: float
    bbox: List[float] = field(default_factory=list)
    portion_g: float = 0.0
    calories: float = 0.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0
    food_item_id: Optional[int] = None
    portion_meta: Optional[str] = None



NON_FOOD_EXCLUDE = {
    "dining table",
    "table",
    "knife",
    "fork",
    "spoon",
    "bowl",
    "cup",
    "wine glass",
    "bottle",
    "water bottle",
    "chair",
    "couch",
    "person",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "bench",
    "potted plant",
    "plate",
}

COCO_FOOD_CLASSES = {
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
}



_PORTION_BRACKETS: List[tuple] = [
    (0.03, 50.0),
    (0.08, 100.0),
    (0.18, 175.0),
    (0.35, 250.0),
    (1.00, 350.0),
]


def estimate_portion_from_bbox(
    bbox: Sequence[float],
    image_width: int,
    image_height: int,
    default_portion_g: float = 150.0,
    food_class: Optional[str] = None,
) -> float:
    portion, _ = estimate_portion_with_geometry(
        bbox=bbox,
        image_width=image_width,
        image_height=image_height,
        default_portion_g=default_portion_g,
        food_class=food_class,
    )
    return portion


def estimate_portion_with_geometry(
    bbox: Sequence[float],
    image_width: int,
    image_height: int,
    default_portion_g: float = 150.0,
    food_class: Optional[str] = None,
) -> tuple[float, Optional[str]]:
    if len(bbox) < 4 or image_width <= 0 or image_height <= 0:
        return default_portion_g, None

    x1, y1, x2, y2 = bbox[:4]
    box_w = max(0.0, x2 - x1)
    box_h = max(0.0, y2 - y1)
    bbox_area = box_w * box_h
    image_area = float(image_width * image_height)

    if image_area == 0 or bbox_area == 0:
        return default_portion_g, None

    relative_area = bbox_area / image_area
    min_dim = min(image_width, image_height)
    norm_food = (food_class or "").lower().strip()

    # Pizza: circular slab model
    if "pizza" in norm_food:
        import math
        d_px = (box_w + box_h) / 2.0
        rel_d = d_px / min_dim

        d_cm = rel_d * 34.0
        d_inches = d_cm / 2.54

        # Distinguish single slice vs personal vs medium vs large whole pizza
        aspect_ratio = max(box_w, box_h) / max(1.0, min(box_w, box_h))
        is_single_slice = relative_area < 0.15 and aspect_ratio > 1.3

        if is_single_slice:
            slice_weight = round(max(95.0, min(175.0, 130.0 * (relative_area / 0.10) ** 0.5)), 1)
            meta = f"Single Slice (Sector ~{d_cm:.1f}cm / {d_inches:.1f}\")"
            return slice_weight, meta

        # Full pizza circular slab: Volume = pi * r^2 * thickness
        r_cm = d_cm / 2.0
        area_cm2 = math.pi * (r_cm ** 2)
        thickness_cm = 1.15
        density_g_cm3 = 0.62

        calculated_grams = area_cm2 * thickness_cm * density_g_cm3

        clamped_grams = round(max(280.0, min(1100.0, calculated_grams)), 1)
        meta = f"Diameter ~{d_cm:.1f}cm ({d_inches:.1f}\") • Cylindrical Slab Model"
        return clamped_grams, meta

    # Fruits/spheres: ellipsoid volume
    if any(k in norm_food for k in ["apple", "orange", "tomato", "peach", "donut"]):
        import math
        d_px = (box_w + box_h) / 2.0
        rel_d = d_px / min_dim
        d_cm = rel_d * 34.0
        d_cm = max(4.5, min(11.0, d_cm))
        r_cm = d_cm / 2.0
        volume_cm3 = (4.0 / 3.0) * math.pi * (r_cm ** 3)
        density = 0.88  # typical fruit density g/cm3
        grams = round(max(60.0, min(350.0, volume_cm3 * density)), 1)
        meta = f"Diameter ~{d_cm:.1f}cm • Ellipsoidal Volume"
        return grams, meta

    # Generic area-bracket fallback
    if food_class is None:
        for max_area, grams in _PORTION_BRACKETS:
            if relative_area <= max_area:
                return grams, None
        return _PORTION_BRACKETS[-1][1], None

    # Continuous scaling based on default serving size
    scale_factor = (relative_area / 0.15) ** 0.60
    estimated = round(max(default_portion_g * 0.4, min(default_portion_g * 3.5, default_portion_g * scale_factor)), 1)
    meta = f"Area Scale ({int(relative_area * 100)}% coverage)"
    return estimated, meta


def scale_nutrition(info: NutritionInfo, portion_g: float) -> dict:
    factor = portion_g / 100.0
    return {
        "calories": round(info.calories_per_100g * factor, 1),
        "protein_g": round(info.protein_per_100g * factor, 1),
        "fat_g": round(info.fat_per_100g * factor, 1),
        "carbs_g": round(info.carbs_per_100g * factor, 1),
    }


def _fuzzy_match_nutrition(
    food_name: str,
    nutrition_lookup: Dict[str, NutritionInfo],
    cutoff: float = 0.55,
) -> Optional[NutritionInfo]:
    import difflib

    food_lower = food_name.lower().strip()

    # Exact match
    if food_lower in nutrition_lookup:
        return nutrition_lookup[food_lower]

    # Substring match
    for key, info in nutrition_lookup.items():
        if key in food_lower or food_lower in key:
            return info
        if info.name.lower() in food_lower or food_lower in info.name.lower():
            return info

    # Fuzzy match
    candidates: Dict[str, NutritionInfo] = {}
    for key, info in nutrition_lookup.items():
        candidates[key] = info
        candidates[info.name.lower()] = info

    best = difflib.get_close_matches(food_lower, candidates.keys(), n=1, cutoff=cutoff)
    if best:
        return candidates[best[0]]

    return None


def _run_gemini_inference(
    image_path: Path,
    nutrition_lookup: Dict[str, NutritionInfo],
    api_key: str,
) -> List[DetectionResult]:
    from app.cv.gemini_vision import identify_foods_with_gemini

    gemini_results = identify_foods_with_gemini(image_path, api_key)

    detections: List[DetectionResult] = []
    for gr in gemini_results:
        info = _fuzzy_match_nutrition(gr.food_name, nutrition_lookup)
        portion = gr.estimated_grams or (info.default_portion_g if info else 150.0)

        if info is not None and info.calories_per_100g > 0:
            scaled = scale_nutrition(info, portion)
            name = info.name
            food_id = info.food_item_id
        else:
            # Use Gemini's direct estimate
            scaled = {
                "calories": round(gr.calories, 1) if gr.calories > 0 else round(1.5 * portion, 1),
                "protein_g": round(gr.protein_g, 1),
                "fat_g": round(gr.fat_g, 1),
                "carbs_g": round(gr.carbs_g, 1),
            }
            name = gr.food_name
            food_id = info.food_item_id if info else None

        detections.append(
            DetectionResult(
                detected_class=name,
                confidence=round(gr.confidence, 4),
                bbox=[],
                portion_g=portion,
                food_item_id=food_id,
                **scaled,
            )
        )

    return detections


def _suppress_and_merge_overlapping_boxes(raw_candidates: List[dict]) -> List[dict]:
    """Suppress sub-slice duplicate detections of the same dish."""
    if not raw_candidates:
        return []

    sorted_cands = sorted(
        raw_candidates,
        key=lambda c: max(0.0, (c["bbox"][2] - c["bbox"][0]) * (c["bbox"][3] - c["bbox"][1])),
        reverse=True,
    )

    kept: List[dict] = []

    for cand in sorted_cands:
        bx1, by1, bx2, by2 = cand["bbox"]
        area_cand = max(1.0, (bx2 - bx1) * (by2 - by1))
        suppress = False

        cand_name = cand["info"].name.lower().strip()

        for existing in kept:
            ex_name = existing["info"].name.lower().strip()

            if cand_name != ex_name:
                continue

            ex1, ey1, ex2, ey2 = existing["bbox"]
            area_ex = max(1.0, (ex2 - ex1) * (ey2 - ey1))

            # Intersection rectangle
            ix1 = max(bx1, ex1)
            iy1 = max(by1, ey1)
            ix2 = min(bx2, ex2)
            iy2 = min(by2, ey2)
            iw = max(0.0, ix2 - ix1)
            ih = max(0.0, iy2 - iy1)
            inter_area = iw * ih

            min_area = min(area_cand, area_ex)
            union_area = area_cand + area_ex - inter_area
            iom = inter_area / min_area  # Containment ratio
            iou = inter_area / max(1.0, union_area)

            if iom > 0.35 or iou > 0.30:
                suppress = True
                if cand["confidence"] > existing["confidence"]:
                    existing["confidence"] = cand["confidence"]
                break

        if not suppress:
            kept.append(cand)

    return kept


def _run_yolo_inference(
    image_path: Path,
    nutrition_lookup: Dict[str, NutritionInfo],
    confidence_threshold: float,
) -> List[DetectionResult]:
    model = get_model()

    try:
        import cv2
        img = cv2.imread(str(image_path))
        if img is None:
            raise FileNotFoundError(f"Cannot read image at {image_path}")
        img_h, img_w = img.shape[:2]
    except ImportError:
        from PIL import Image
        with Image.open(str(image_path)) as img_pil:
            img_w, img_h = img_pil.size

    results = model.predict(
        source=str(image_path),
        conf=confidence_threshold,
        verbose=False,
    )

    raw_candidates: List[dict] = []

    for result in results:
        if result.boxes is None:
            continue
        boxes = result.boxes
        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            conf = float(boxes.conf[i].item())
            xyxy = boxes.xyxy[i].tolist()
            class_name = model.names.get(cls_id, f"class_{cls_id}")
            clean_name = class_name.lower().strip()

            if clean_name in NON_FOOD_EXCLUDE:
                logger.info("Filtered non-food object: %s (conf=%.2f)", class_name, conf)
                continue

            info = nutrition_lookup.get(clean_name)
            if info is None:
                info = _fuzzy_match_nutrition(clean_name, nutrition_lookup)

            if info is None:
                if clean_name in COCO_FOOD_CLASSES:
                    info = NutritionInfo(name=clean_name)
                else:
                    logger.info("Discarding non-food class: %s", class_name)
                    continue

            # If nutrition info has 0 calories and not in COCO foods, discard
            if info.calories_per_100g == 0 and clean_name not in COCO_FOOD_CLASSES:
                continue

            raw_candidates.append({
                "class_name": class_name,
                "confidence": conf,
                "bbox": xyxy,
                "info": info,
            })

    filtered_candidates = _suppress_and_merge_overlapping_boxes(raw_candidates)

    detections: List[DetectionResult] = []

    for cand in filtered_candidates:
        xyxy = cand["bbox"]
        info = cand["info"]
        class_name = cand["class_name"]
        conf = cand["confidence"]

        portion, meta = estimate_portion_with_geometry(
            bbox=xyxy,
            image_width=img_w,
            image_height=img_h,
            default_portion_g=info.default_portion_g,
            food_class=info.name if info.name != "unknown" else class_name,
        )

        scaled = scale_nutrition(info, portion)

        detections.append(
            DetectionResult(
                detected_class=info.name if info.name != "unknown" else class_name,
                confidence=round(conf, 4),
                bbox=[round(v, 1) for v in xyxy],
                portion_g=portion,
                food_item_id=info.food_item_id,
                portion_meta=meta,
                **scaled,
            )
        )

    return detections


def run_inference(
    image_path: str | Path,
    nutrition_lookup: Dict[str, NutritionInfo],
    confidence_threshold: Optional[float] = None,
    gemini_api_key: Optional[str] = None,
) -> List[DetectionResult]:
    if confidence_threshold is None:
        try:
            from app.core.config import get_settings
            confidence_threshold = get_settings().YOLO_CONFIDENCE_THRESHOLD
        except Exception:
            confidence_threshold = 0.25

    image_path = Path(image_path)

    if not gemini_api_key:
        try:
            from app.core.config import get_settings
            gemini_api_key = get_settings().GEMINI_API_KEY
        except Exception:
            pass

    if gemini_api_key:
        try:
            logger.info("Using Gemini Vision for food identification ...")
            detections = _run_gemini_inference(image_path, nutrition_lookup, gemini_api_key)
            if detections:
                logger.info("Gemini: %d detection(s) in %s", len(detections), image_path.name)
                return detections
            logger.warning("Gemini returned 0 detections; falling back to YOLO.")
        except Exception as exc:
            logger.error("Gemini Vision failed (%s)", exc)
            raise RuntimeError(f"Gemini Vision failed: {exc}")

    # Fallback: YOLO COCO
    logger.info("Using YOLO COCO (conf=%.2f) ...", confidence_threshold)
    detections = _run_yolo_inference(image_path, nutrition_lookup, confidence_threshold)
    logger.info("YOLO: %d detection(s) in %s", len(detections), image_path.name)
    return detections
