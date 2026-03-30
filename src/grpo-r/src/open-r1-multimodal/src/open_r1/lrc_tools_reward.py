import json
from json_repair import repair_json
from scipy.optimize import linear_sum_assignment
import os
import numpy as np
from scipy.interpolate import CubicSpline

# sol: ground truth value
# content: predicted value
def roa_reward(content, sol, type="global_param_matching", **kwargs):
    try:
        gt_params = json.loads(repair_json(sol))
        pred_params = json.loads(content)
    except:
        try:
            # If direct parsing fails, try using json_repair to repair
            repaired_json = repair_json(content)
            pred_params = json.loads(repaired_json)
        except:
            print("Error: Failed to repair JSON")
            return 0.0  # Return 0 score for JSON parsing failure
    
    # If prediction is a list, take the last element
    if isinstance(pred_params, list):
        pred_params = pred_params[-1]

    # Validate parameters
    if (pred_params is None or gt_params is None or 
        not isinstance(pred_params, dict) or not isinstance(gt_params, dict) or 
        len(pred_params) == 0 or len(gt_params) == 0):
        print("Error: Invalid JSON format")
        print(f"pred_params: {pred_params}")
        return 0.0
    
    if type == "global_param_matching":
        # 1. Global parameter accuracy (60%)
        try:
            global_param_score = calculate_global_param_matching(pred_params, gt_params)
        except Exception as e:
            print(f"Global param error: {e}")
            global_param_score = 0.0
        return global_param_score
    elif type == "global_param_accuracy":
        try:
            global_param_score = calculate_global_param_accuracy(pred_params, gt_params)
        except Exception as e:
            print(f"Global param error: {e}")
            global_param_score = 0.0
        return global_param_score
    elif type == "mask_accuracy":
        # 2. Mask matching and local parameters (40%)
        try:
            mask_score = evaluate_masks(pred_params, gt_params)
        except Exception as e:
            print(f"Mask error: {e}")
            mask_score = 0.0
        return mask_score
    else:
        raise ValueError(f"Invalid type: {type}")

    
def calculate_global_param_matching(pred, gt):
    # Exclude mask parameters, focus on basic adjustment parameters
    exclude_keys = ['UprightVersion', 'UprightFourSegmentsCount', 'UprightCenterMode', 'UprightPreview', 'UprightVersion',
                    'PerspectiveUpright', 'UprightFocalMode', 'UprightTransformCount', 'MaskGroupBasedCorrections', 'PresetType',
                    'Cluster', 'UUID', 'SupportsAmount2', 'SupportsAmount', 'SupportsColor', 'SupportsMonochrome', 'SupportsHighDynamicRange',
                    'SupportsNormalDynamicRange', 'SupportsSceneReferred', 'SupportsOutputReferred', 'CameraModelRestriction', 'Copyright', 'ContactInfo',
                    'ProcessVersion', 'HasSettings', 'LensProfileEnable', 'LensManualDistortionAmount', 'VignetteAmount', 'DefringePurpleAmount',
                    'DefringePurpleHueLo', 'DefringePurpleHueHi', 'DefringeGreenAmount', 'DefringeGreenHueLo', 'DefringeGreenHueHi', 'PerspectiveVertical',
                    'PerspectiveHorizontal', 'PerspectiveRotate', 'PerspectiveAspect', 'PerspectiveScale', 'PerspectiveX', 'PerspectiveY', 'HDREditMode', 'CropConstrainToWarp',
                    'CompatibleVersion'
                ]
    pp3_keys = ['ToneCurvePV2012', 'ToneCurvePV2012Red', 'ToneCurvePV2012Green', 'ToneCurvePV2012Blue', 'Temperature', 'IncrementalTemperature', 'Tint', 'IncrementalTint', 'Exposure2012', 'Contrast2012', 'Saturation', 'Vibrance', 'Highlights2012', 'Shadows2012']

    # Extract parameter name sets (exclude masks and irrelevant parameters)
    excluded_prefixes = ('HueAdjustment', 'SaturationAdjustment', 'LuminanceAdjustment')
    
    # More efficient filtering using list comprehension with combined conditions
    gt_keys = {k for k in gt.keys() 
               if k not in exclude_keys and 
               k in pp3_keys and 
               not any(k.startswith(prefix) for prefix in excluded_prefixes)}
    
    pred_keys = {k for k in pred.keys() 
                if k not in exclude_keys and 
                k in pp3_keys and 
                not any(k.startswith(prefix) for prefix in excluded_prefixes)}

    # Calculate intersection and union
    intersection = gt_keys & pred_keys
    union = gt_keys | pred_keys

    # Accuracy
    if not union:
        return 1.0  # No parameters, considered as perfect match
    return len(intersection) / len(union)

def calculate_global_param_accuracy(pred, gt):
    exclude_keys = ['UprightVersion', 'UprightFourSegmentsCount', 'UprightCenterMode', 'UprightPreview', 'UprightVersion',
                    'PerspectiveUpright', 'UprightFocalMode', 'UprightTransformCount', 'MaskGroupBasedCorrections', 'PresetType',
                    'Cluster', 'UUID', 'SupportsAmount2', 'SupportsAmount', 'SupportsColor', 'SupportsMonochrome', 'SupportsHighDynamicRange',
                    'SupportsNormalDynamicRange', 'SupportsSceneReferred', 'SupportsOutputReferred', 'CameraModelRestriction', 'Copyright', 'ContactInfo',
                    'ProcessVersion', 'HasSettings', 'LensProfileEnable', 'LensManualDistortionAmount', 'VignetteAmount', 'DefringePurpleAmount',
                    'DefringePurpleHueLo', 'DefringePurpleHueHi', 'DefringeGreenAmount', 'DefringeGreenHueLo', 'DefringeGreenHueHi', 'PerspectiveVertical',
                    'PerspectiveHorizontal', 'PerspectiveRotate', 'PerspectiveAspect', 'PerspectiveScale', 'PerspectiveX', 'PerspectiveY', 'HDREditMode', 'CropConstrainToWarp',
                    'CompatibleVersion'
                ]
    pp3_keys = ['ToneCurvePV2012', 'ToneCurvePV2012Red', 'ToneCurvePV2012Green', 'ToneCurvePV2012Blue', 'Temperature', 'IncrementalTemperature', 'Tint', 'IncrementalTint', 'Exposure2012', 'Contrast2012', 'Saturation', 'Vibrance', 'Highlights2012', 'Shadows2012']

    # Extract parameter name sets (exclude masks and irrelevant parameters)
    excluded_prefixes = ('HueAdjustment', 'SaturationAdjustment', 'LuminanceAdjustment')
    
    gt_keys = {k for k in gt.keys() 
               if k not in exclude_keys and 
               k in pp3_keys and 
               not any(k.startswith(prefix) for prefix in excluded_prefixes)}
    
    pred_keys = {k for k in pred.keys() 
                if k not in exclude_keys and 
                k in pp3_keys and 
                not any(k.startswith(prefix) for prefix in excluded_prefixes)}

    # Calculate intersection
    intersection = gt_keys & pred_keys

    param_score = 0.0
    param_count = 0
    
    # Special dictionary parameter handlers
    special_handlers = {
        "ToneCurvePV2012": lambda p, g: handle_tone_curve(p, g),
        "ToneCurvePV2012Red": lambda p, g: handle_tone_curve(p, g),
        "ToneCurvePV2012Green": lambda p, g: handle_tone_curve(p, g),
        "ToneCurvePV2012Blue": lambda p, g: handle_tone_curve(p, g),
        "PointColors": lambda p, g: handle_point_colors(p, g),
        "LensBlur": lambda p, g: handle_lens_blur(p, g),
        "Look": lambda p, g: handle_look(p, g)
    }
    
    for key in intersection:
        # Handle special dictionary parameters
        if isinstance(gt[key], dict):
            if key in special_handlers:
                result = special_handlers[key](pred[key], gt[key])
                if result is not None:
                    score, count = result
                    param_score += score
                    param_count += count
                continue
        
        param_count += 1
        try:
            # Calculate score based on parameter type
            if isinstance(gt[key], bool):
                # Boolean parameters: exact match
                param_score += 1.0 if gt[key] == pred[key] else 0.0
            elif isinstance(gt[key], (int, float)):
                # Numeric parameters: calculate score based on relative error
                diff = abs(gt[key] - pred[key])
                threshold = get_param_thresholds(key)
                
                # If error is within threshold, give score
                if diff <= threshold:
                    param_score += 1.0 - (diff / threshold)
                else:
                    param_score += 0.0
            else:
                # String and other parameters: exact match
                param_score += 1.0 if gt[key] == pred[key] else 0.0
        except:
            # Don't increase count on error
            param_count -= 1

    # Return average score
    return param_score / max(1, param_count)

# Helper functions for special parameter handling
def handle_tone_curve(pred, gt):
    if len(gt) > 0:
        curve_score, is_add = compare_tone_curves(pred, gt)
        # Only add positive scores
        if is_add:
            return curve_score, 1
    return None

def handle_point_colors(pred, gt):
    if len(gt) > 0:
        point_colors_score = compare_point_colors(pred, gt)
        return point_colors_score, 1
    return None

def handle_lens_blur(pred, gt):
    if "Active" in gt and gt["Active"] == True:
        if "Active" in pred and pred["Active"] == True:
            return 1.0, 1
    return None

def handle_look(pred, gt):
    if len(gt) > 0:
        if len(pred) == 0:
            return 0, 1
        else:
            amount_diff = max(0, 1 - abs(gt.get("Amount", 1) - pred.get("Amount", 1)))
            look_param_score = amount_diff * get_look_param_score(gt.get("Param", None), pred.get("Param", None))
            return look_param_score, 1
    return None

def evaluate_masks(pred, gt):
    # Check if both sides have masks
    if "MaskGroupBasedCorrections" not in gt or "MaskGroupBasedCorrections" not in pred:
        return 0.0 if "MaskGroupBasedCorrections" in gt else 1.0
    
    gt_masks = gt["MaskGroupBasedCorrections"]
    pred_masks = pred["MaskGroupBasedCorrections"]
    
    # If one side is an empty list
    if not gt_masks:
        return 1.0 if not pred_masks else 0.0
    if not pred_masks:
        return 0.0
    
    # 1. First match mask regions
    mask_matches, cost_matrix = match_masks(pred_masks, gt_masks)
    
    # 2. Calculate scores for matched masks
    total_score = 0.0
    
    for pred_idx, gt_idx in mask_matches:
        # If a match is found, calculate parameter score for that mask
        pred_mask = pred_masks[pred_idx]
        gt_mask = gt_masks[gt_idx]
        
        # Calculate mask region match score (50%)
        region_score = 1.0 - cost_matrix[pred_idx][gt_idx]
        
        # Calculate mask parameter match score (50%)
        param_score = calculate_mask_param_accuracy(pred_mask, gt_mask)
        
        # Combined score
        total_score += region_score * param_score
    
    # Matched masks count / total masks count
    match_ratio = len(mask_matches) / len(gt_masks)
    
    # Mask match ratio + average score of matched masks
    avg_mask_score = total_score / len(mask_matches) if mask_matches else 0.0
    
    # Final mask score: weighted average of match ratio and average score
    final_mask_score = 0.4 * match_ratio + 0.6 * avg_mask_score
    
    return final_mask_score

def match_masks(pred_masks, gt_masks):
    # Use Hungarian algorithm to match masks
    # Returns [(pred_idx, gt_idx), ...] match list
    
    # Build cost matrix
    cost_matrix = []
    for pred_mask in pred_masks:
        row = []
        for gt_mask in gt_masks:
            # Calculate similarity between two masks as cost
            similarity = calculate_mask_similarity(pred_mask, gt_mask)
            # Convert to cost (1-similarity)
            row.append(1.0 - similarity)
        cost_matrix.append(row)
    
    # Use Hungarian algorithm to find optimal matching
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    # Filter out matches with low similarity
    similarity_threshold = 0.3  # Minimum similarity of 0.3
    cost_threshold = 0.7  # 1.0 - similarity_threshold
    
    matches = [(i, j) for i, j in zip(row_ind, col_ind) if cost_matrix[i][j] < cost_threshold]
    
    return matches, cost_matrix

def calculate_mask_similarity(pred_mask, gt_mask):
    # Calculate similarity between different types of masks
    
    # Check if both have CorrectionMasks
    if "CorrectionMasks" not in pred_mask or "CorrectionMasks" not in gt_mask:
        return 0.0
    
    pred_submasks = pred_mask["CorrectionMasks"]
    gt_submasks = gt_mask["CorrectionMasks"]
    
    if not pred_submasks or not gt_submasks:
        return 0.0
    
    # Handle multiple CorrectionMasks
    # Build cost matrix
    cost_matrix = []
    
    # Define mask type comparison function
    def get_submask_similarity(pred_submask, gt_submask):
        # Calculate similarity between individual submasks
        if "What" not in pred_submask or pred_submask["What"] != gt_submask.get("What", ""):
            return 0.1  # Different mask types get minimum similarity
        
        # Calculate similarity based on mask type
        mask_type = pred_submask["What"]
        
        if "Gradient" in mask_type:
            # Linear or radial gradient
            return compare_gradient_masks(pred_submask, gt_submask, mask_type)
        elif "Mask/RangeMask" in mask_type:
            # Color range or luminance range
            return compare_range_masks(pred_submask, gt_submask)
        elif "MaskSubType" in gt_submask:
            # AI detection mask
            return compare_ai_masks(pred_submask, gt_submask)
        else:
            # Other mask types, check basic attributes only
            return compare_basic_mask_attributes(pred_submask, gt_submask)
    
    # Build cost matrix with similarities
    for pred_submask in pred_submasks:
        row = [1.0 - get_submask_similarity(pred_submask, gt_submask) for gt_submask in gt_submasks]
        cost_matrix.append(row)
    
    # Handle empty matrix case
    if not cost_matrix:
        return 0.0
    
    # Balance rows and columns for Hungarian algorithm
    if len(pred_submasks) > len(gt_submasks):
        # More predictions than ground truth, add virtual rows
        for _ in range(len(pred_submasks) - len(gt_submasks)):
            cost_matrix.append([0.9] * len(gt_submasks))  # 0.9 represents low similarity but non-zero
    elif len(gt_submasks) > len(pred_submasks):
        # More ground truth than predictions, add virtual columns
        for row in cost_matrix:
            row.extend([0.9] * (len(gt_submasks) - len(pred_submasks)))
    
    # Find optimal assignment
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    # Calculate average similarity of matches
    total_similarity = 0.0
    valid_matches = 0
    similarity_threshold = 0.2
    
    for i, j in zip(row_ind, col_ind):
        # Check if this is a valid match (not virtually added)
        if i < len(pred_submasks) and j < len(gt_submasks):
            # Check if similarity is high enough
            similarity = 1.0 - cost_matrix[i][j]
            if similarity > similarity_threshold:  # Only consider matches with similarity at least 0.2
                total_similarity += similarity
                valid_matches += 1
    
    # Calculate completeness score: matches/total
    completeness = min(
        valid_matches / max(1, len(pred_submasks)),
        valid_matches / max(1, len(gt_submasks))
    )
    
    # If no valid matches
    if valid_matches == 0:
        return 0.0
    
    # Final score: average similarity(70%) + completeness(30%)
    final_similarity = (
        0.7 * (total_similarity / valid_matches) + 
        0.3 * completeness
    )
    
    return final_similarity

def compare_gradient_masks(pred, gt, mask_type):
    # Compare gradient masks
    similarity = 0.0
    
    # Check basic attributes
    basic_sim = compare_basic_mask_attributes(pred, gt)
    
    # Check gradient points based on different gradient types
    position_sim = 0.0
    
    if "Mask/Gradient" in mask_type:
        # Linear gradient
        if all(k in pred and k in gt for k in ["ZeroX", "ZeroY", "FullX", "FullY"]):
            # Calculate Euclidean distance between start and end points
            start_dist = ((pred["ZeroX"] - gt["ZeroX"])**2 + (pred["ZeroY"] - gt["ZeroY"])**2)**0.5
            end_dist = ((pred["FullX"] - gt["FullX"])**2 + (pred["FullY"] - gt["FullY"])**2)**0.5
            
            # Convert to similarity
            start_sim = max(0, 1 - start_dist/0.5)  # Distance above 0.5 is considered completely different
            end_sim = max(0, 1 - end_dist/0.5)
            
            position_sim = (start_sim + end_sim) / 2
    
    elif "Mask/CircularGradient" in mask_type:
        # Radial gradient
        if all(k in pred and k in gt for k in ["Top", "Left", "Bottom", "Right"]):
            # Calculate center point and radius
            pred_center_x = (pred["Left"] + pred["Right"]) / 2
            pred_center_y = (pred["Top"] + pred["Bottom"]) / 2
            gt_center_x = (gt["Left"] + gt["Right"]) / 2
            gt_center_y = (gt["Top"] + gt["Bottom"]) / 2
            
            # Calculate width and height
            pred_width = abs(pred["Right"] - pred["Left"])
            pred_height = abs(pred["Bottom"] - pred["Top"])
            gt_width = abs(gt["Right"] - gt["Left"])
            gt_height = abs(gt["Bottom"] - gt["Top"])
            
            # Calculate center point distance
            center_dist = ((pred_center_x - gt_center_x)**2 + (pred_center_y - gt_center_y)**2)**0.5
            
            # Calculate size difference
            size_diff = abs(pred_width/gt_width - 1) + abs(pred_height/gt_height - 1)
            
            # Convert to similarity
            center_sim = max(0, 1 - center_dist/0.5)  # Center point distance
            size_sim = max(0, 1 - size_diff/1.0)      # Size ratio difference
            
            # If angle parameter exists, also calculate angle difference
            angle_sim = 1.0
            if "Angle" in pred and "Angle" in gt:
                # Calculate angle difference, note angles may be 360-degree cyclic
                angle_diff = min(
                    abs(pred["Angle"] - gt["Angle"]),
                    360 - abs(pred["Angle"] - gt["Angle"])
                ) / 180.0  # Normalize to 0-1
                angle_sim = max(0, 1 - angle_diff)
                
                # Combined position similarity: center(40%) + size(40%) + angle(20%)
                position_sim = 0.4 * center_sim + 0.4 * size_sim + 0.2 * angle_sim
            else:
                # Without angle parameter: center(50%) + size(50%)
                position_sim = 0.5 * center_sim + 0.5 * size_sim
    
    # Final similarity: basic attributes(30%) + position(70%)
    similarity = basic_sim * position_sim
    
    return similarity

def compare_ai_masks(pred, gt):
    # Compare AI detection masks
    
    # Check mask subtype
    pred_subtype = pred.get("MaskSubType")
    gt_subtype = gt.get("MaskSubType")
    
    if pred_subtype != gt_subtype:
        # If one is object(0) and one is subject(1), give some similarity
        if {pred_subtype, gt_subtype} == {0, 1}:
            return 0.4  # Similarity between object and subject is 0.4
        else:
            return 0  # Other non-matching subtypes get low similarity
    
    # For face and other specific category detections
    if "MaskSubCategoryID" in gt:
        if pred.get("MaskSubCategoryID") != gt.get("MaskSubCategoryID"):
            return 0.3  # Categories don't match but detection type is the same
    
    # For object detection (MaskSubType=0), check bounding box
    if pred_subtype == 0 and "Gesture" in pred and "Gesture" in gt:
        # Extract bounding box information
        pred_box = get_polygon_bbox(pred["Gesture"])
        gt_box = get_polygon_bbox(gt["Gesture"])
        
        if pred_box and gt_box:
            # Calculate IoU (Intersection over Union)
            iou_score = calculate_iou(pred_box, gt_box)
            
            # Basic attribute comparison
            basic_sim = compare_basic_mask_attributes(pred["Gesture"][0], gt["Gesture"][0])
            
            # Final similarity: basic attributes(20%) + bounding box IoU(80%)
            return basic_sim * iou_score
    
    # Basic attribute comparison
    basic_sim = compare_basic_mask_attributes(pred, gt)
    
    return basic_sim

def get_polygon_bbox(gesture_list):
    """Extract bounding box from polygon gesture"""
    if not gesture_list or len(gesture_list) == 0:
        return None
    
    # Try to get points from the first gesture
    try:
        # If it's a polygon
        if "Points" in gesture_list[0]:
            points = gesture_list[0]["Points"]
            
            # Extract all X and Y coordinates
            x_coords = [point["X"] for point in points]
            y_coords = [point["Y"] for point in points]
            
            # Calculate bounding box [xmin, ymin, xmax, ymax]
            return [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
        
        # If it's already in bounding box format
        elif all(k in gesture_list[0] for k in ["Left", "Top", "Right", "Bottom"]):
            return [
                gesture_list[0]["Left"], 
                gesture_list[0]["Top"], 
                gesture_list[0]["Right"], 
                gesture_list[0]["Bottom"]
            ]
    except Exception:
        pass
    
    return None

def calculate_iou(box1, box2):
    """Calculate IoU (Intersection over Union) between two bounding boxes"""
    # Ensure input is in bounding box format [xmin, ymin, xmax, ymax]
    xmin1, ymin1, xmax1, ymax1 = box1
    xmin2, ymin2, xmax2, ymax2 = box2
    
    # Calculate intersection area
    x_left = max(xmin1, xmin2)
    y_top = max(ymin1, ymin2)
    x_right = min(xmax1, xmax2)
    y_bottom = min(ymax1, ymax2)
    
    # Check if boxes overlap
    if x_right < x_left or y_bottom < y_top:
        return 0  # No overlap
    
    # Calculate areas
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    box1_area = (xmax1 - xmin1) * (ymax1 - ymin1)
    box2_area = (xmax2 - xmin2) * (ymax2 - ymin2)
    
    # Calculate union area
    union_area = box1_area + box2_area - intersection_area
    
    # Calculate IoU
    if union_area <= 0:
        return 0
    
    return intersection_area / union_area

def compare_basic_mask_attributes(pred, gt):
    # Compare basic attributes of two masks
    attributes = [
        "MaskActive", "MaskInverted", "MaskBlendMode", "MaskValue"
    ]
    
    # Check if mask is active - critical attribute
    if pred.get("MaskActive", True) != gt.get("MaskActive", True):
        return 0.0
    
    # Check if mask is inverted - critical attribute
    if pred.get("MaskInverted", False) != gt.get("MaskInverted", False):
        return 0.0
    
    # Check blend mode - important but not critical
    if pred.get("MaskBlendMode", 0) != gt.get("MaskBlendMode", 0):
        return 0.4
    
    # Check mask value - calculate similarity based on difference
    mask_value_pred = pred.get("MaskValue", 1)
    mask_value_gt = gt.get("MaskValue", 1)
    if mask_value_pred != mask_value_gt:
        return 1.0 - abs(mask_value_pred - mask_value_gt)
    
    # All attributes match
    return 1.0


def calculate_mask_param_accuracy(pred_mask, gt_mask):
    # Calculate accuracy of mask adjustment parameters
    param_score = 0.0
    param_count = 0
    
    # Get union of all parameters
    all_params = set(pred_mask.keys()).union(set(gt_mask.keys()))
    
    # Exclude non-parameter fields
    exclude_params = ["What", "CorrectionMasks", "CorrectionName", "Gesture", "LocalCurveRefineSaturation", "CorrectionAmount"]
    special_params = ["LocalPointColors", "MainCurve", "RedCurve", "GreenCurve", "BlueCurve"]
    param_keys = [param for param in all_params if param not in exclude_params]
    
    # Parameters only in prediction
    only_pred_params = [param for param in param_keys if param not in gt_mask]
    
    # Process regular parameters
    for param in param_keys:
        # Skip special parameters, handle separately
        if param in special_params:
            continue
        
        # Default values based on type
        default_values = {
            bool: True,
            int: 0,
            float: 0.0,
            str: ""
        }
            
        # Get parameter values with defaults if needed
        if param in gt_mask:
            gt_value = gt_mask[param]
            pred_value = pred_mask.get(param, None)
            
            # If parameter doesn't exist in prediction, set default value based on type
            if pred_value is None:
                for typ, default in default_values.items():
                    if isinstance(gt_value, typ):
                        pred_value = default
                        break
                if pred_value is None:  # If no matching type found
                    pred_value = ""
        else:
            # If parameter doesn't exist in ground truth but exists in prediction
            if param in pred_mask:
                pred_value = pred_mask[param]
                
                # Set default ground truth value based on prediction type
                for typ, default in default_values.items():
                    if isinstance(pred_value, typ):
                        gt_value = default
                        break
                if 'gt_value' not in locals():  # If no matching type found
                    gt_value = ""
            else:
                # Neither side has it, skip
                continue
        
        param_count += 1
        
        # Calculate score based on parameter type
        if isinstance(gt_value, bool):
            # Boolean type, exact match or 0 score
            param_score += 1.0 if gt_value == pred_value and param not in only_pred_params else 0.0 
        elif isinstance(gt_value, (int, float)) and isinstance(pred_value, (int, float)):
            # Numeric type, calculate relative error based on threshold
            threshold = get_param_thresholds(param)
            diff = abs(gt_value - pred_value)
            
            # Skip parameters only in prediction with small differences
            if param in only_pred_params and diff/threshold < 0.5:
                param_count -= 1
                continue
                
            # If error is within threshold, give score
            param_score += max(0.0, 1.0 - (diff / threshold)) if diff <= threshold else 0.0
        else:
            # Other types (strings, etc.), exact match or 0 score
            if param not in only_pred_params:
                param_score += 1.0 if gt_value == pred_value else 0.0
    
    # Handle special parameters
    special_param_score = 0.0
    special_param_count = 0
    
    # 1. Handle LocalPointColors
    if "LocalPointColors" in gt_mask or "LocalPointColors" in pred_mask:
        point_colors_score = compare_local_point_colors(
            pred_mask.get("LocalPointColors", {}), 
            gt_mask.get("LocalPointColors", {})
        )
        if point_colors_score is not None and not ("LocalPointColors" in only_pred_params and point_colors_score > 0):
            special_param_score += point_colors_score
            special_param_count += 1
    
    # 2. Handle various curves
    default_curve = {"1": "0,0", "2": "255,255"}
    for curve_type in ["MainCurve", "RedCurve", "GreenCurve", "BlueCurve"]:
        if curve_type in gt_mask or curve_type in pred_mask:
            curve_score = compare_local_curves(
                pred_mask.get(curve_type, default_curve), 
                gt_mask.get(curve_type, default_curve)
            )
            if curve_score is not None and not (curve_type in only_pred_params and curve_score > 0):
                special_param_score += curve_score
                special_param_count += 1
    
    # Combine regular and special parameter scores
    total_count = param_count + special_param_count
    total_score = param_score + special_param_score
    
    # If no parameters to compare, return high score (empty masks shouldn't be penalized)
    if total_count == 0:
        return 1.0
    
    # Return average score
    return total_score / total_count

def compare_local_point_colors(pred_points, gt_points):
    """Compare LocalPointColors parameters, supporting cases where keys differ but content is the same"""
    if not pred_points and not gt_points:
        return 1.0  # Both empty, considered perfect match
    
    if not pred_points or not gt_points:
        return 0.0  # One empty but the other not, considered complete mismatch
    
    # Extract all point sets and parse them
    pred_values_list = []
    for key in pred_points:
        try:
            values = [float(x.strip()) for x in pred_points[key].split(",")]
            pred_values_list.append(values)
        except:
            # If parsing fails, add an empty list as placeholder
            pred_values_list.append([-1]*19)
    
    gt_values_list = []
    for key in gt_points:
        try:
            values = [float(x.strip()) for x in gt_points[key].split(",")]
            gt_values_list.append(values)
        except:
            gt_values_list.append([-1]*19)
    
    # If quantities don't match, pad with empty values
    while len(pred_values_list) < len(gt_values_list):
        pred_values_list.append([-1]*19)
    while len(gt_values_list) < len(pred_values_list):
        gt_values_list.append([-1]*19)
    
    # Build cost matrix - calculate similarity between each pair of point sets
    cost_matrix = []
    for pred_values in pred_values_list:
        row = []
        for gt_values in gt_values_list:
            # If one side is empty, low similarity
            if not pred_values or not gt_values:
                row.append(0.9)  # High cost (low similarity)
                continue
            
            # Different lengths, lower similarity
            if len(pred_values) != len(gt_values):
                row.append(0.7)
                continue
            
            # Calculate Euclidean distance
            dist = sum((p - g)**2 for p, g in zip(pred_values, gt_values)) ** 0.5
            # Convert to cost (1-similarity)
            point_sim = max(0, 1 - dist/10.0)  # Distance above 10 considered completely different
            row.append(1.0 - point_sim)  # Convert to cost
            
        cost_matrix.append(row)
    
    # Use Hungarian algorithm to find optimal matching
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    # Calculate total similarity
    total_similarity = 0.0
    for i, j in zip(row_ind, col_ind):
        similarity = 1.0 - cost_matrix[i][j]
        total_similarity += similarity
    
    # Return average similarity
    return total_similarity / len(row_ind) if row_ind.size > 0 else 1.0

def compare_local_curves(pred_curve, gt_curve):
    """Compare curve parameters and calculate similarity"""
    
    try:
        # Parse predicted curve points
        pred_points = []
        for key in sorted(pred_curve.keys(), key=lambda k: int(k)):
            x, y = map(float, pred_curve[key].split(","))
            pred_points.append((x, y))
        
        # Parse ground truth curve points
        gt_points = []
        for key in sorted(gt_curve.keys(), key=lambda k: int(k)):
            x, y = map(float, gt_curve[key].split(","))
            gt_points.append((x, y))
        
        # Extract x and y coordinates
        pred_x = np.array([p[0] for p in pred_points])
        pred_y = np.array([p[1] for p in pred_points])
        gt_x = np.array([p[0] for p in gt_points])
        gt_y = np.array([p[1] for p in gt_points])
        
        # Create cubic interpolation
        pred_cs = CubicSpline(pred_x, pred_y, bc_type='natural')
        gt_cs = CubicSpline(gt_x, gt_y, bc_type='natural')
        
        # Generate dense points for comparison
        x_dense = np.linspace(0, 255, 500)
        pred_y_dense = pred_cs(x_dense)
        gt_y_dense = gt_cs(x_dense)
        
        # Calculate RMSE
        rmse = np.sqrt(np.mean((pred_y_dense - gt_y_dense) ** 2))
        
        # Convert RMSE to similarity score
        if rmse <= 10:
            # Difference less than 10, score decreases linearly from 1.0 to 0.0
            curve_sim = 1.0 - (rmse / 10.0)
        elif rmse <= 20:
            # Difference between 10 and 20, score decreases linearly from 0.0 to -0.5
            curve_sim = -0.5 * (rmse - 10) / 10
        elif rmse <= 40:
            # Difference between 20 and 40, score decreases linearly from -0.5 to -1.0
            curve_sim = -0.5 - 0.5 * (rmse - 20) / 20
        else:
            # Difference greater than 40, fixed at -1.0
            curve_sim = -1.0
        
        return curve_sim
    except Exception as e:
        # Parsing or comparison error, return low but non-zero score
        return 0.1

def get_param_range(param_name):
    # Return typical range for each parameter
    ranges = {
        # Basic parameters
        "Temperature": 10000,  # Typical range 2000-12000
        "Tint": 100,           # Typical range -50 to +50
        "Exposure2012": 5,     # Typical range -5 to +5
        "Contrast2012": 100,   # Typical range -100 to +100
        "Highlights2012": 100, # Typical range -100 to +100
        "Shadows2012": 100,    # Typical range -100 to +100
        "Whites2012": 100,     # Typical range -100 to +100
        "Blacks2012": 100,     # Typical range -100 to +100
        "Clarity2012": 100,    # Typical range -100 to +100
        "Texture": 100,        # Typical range -100 to +100
        "Dehaze": 100,         # Typical range -100 to +100
        "Saturation": 100,     # Typical range -100 to +100
        "Vibrance": 100,       # Typical range -100 to +100
        
        # Local adjustment parameters
        "LocalExposure2012": 4,     # Typical range -4 to +4
        "LocalContrast2012": 100,   # Typical range -100 to +100
        "LocalHighlights2012": 100, # Typical range -100 to +100
        "LocalShadows2012": 100,    # Typical range -100 to +100
        "LocalWhites2012": 100,     # Typical range -100 to +100
        "LocalBlacks2012": 100,     # Typical range -100 to +100
        "LocalClarity2012": 100,    # Typical range -100 to +100
        "LocalDehaze": 100,         # Typical range -100 to +100
        "LocalTexture": 100,        # Typical range -100 to +100
        
        # Other adjustments
        "Sharpness": 150,      # Typical range 0 to +150
        "SharpenRadius": 3,    # Typical range 0.5 to +3
        "ColorNoiseReduction": 100,  # Typical range 0 to +100
        
        # Default range
        "DEFAULT": 100         # Default range
    }
    
    return ranges.get(param_name, ranges["DEFAULT"])


def get_param_thresholds(param_name):
    # Parameter threshold dictionary - maximum acceptable error for each parameter
    param_thresholds = {
        # Common parameter thresholds
        "Exposure2012": 1,
        "Contrast2012": 70,
        "Highlights2012": 55,
        "Temperature": 1500,
        "Tint": 25,
        "Shadows2012": 55,
        "Whites2012": 50,
        "Blacks2012": 50,
        "Texture": 40,
        "Clarity2012": 30,
        "Dehaze": 20,
        "Vibrance": 30,
        "Saturation": 30,
        "ParametricShadows": 20,
        "ParametricDarks": 20,
        "ParametricLights": 20,
        "ParametricHighlights": 40,
        "ParametricShadowSplit": 40,
        "ParametricMidtoneSplit": 40,
        "ParametricHighlightSplit": 40,
        "RedHue": 20,
        "RedSaturation": 20,
        "GreenHue": 20,
        "GreenSaturation": 20,
        "BlueHue": 20,
        "BlueSaturation": 20,
        "HueAdjustmentRed": 20,
        "HueAdjustmentOrange": 20,
        "HueAdjustmentYellow": 20,
        "HueAdjustmentGreen": 20,
        "HueAdjustmentAqua": 20,
        "HueAdjustmentBlue": 20,
        "HueAdjustmentPurple": 20,
        "HueAdjustmentMagenta": 20,
        "SaturationAdjustmentRed": 20,
        "SaturationAdjustmentOrange": 20,
        "SaturationAdjustmentYellow": 20,
        "SaturationAdjustmentGreen": 20,
        "SaturationAdjustmentAqua": 20,
        "SaturationAdjustmentBlue": 20,
        "SaturationAdjustmentPurple": 20,
        "SaturationAdjustmentMagenta": 20,
        "LuminanceAdjustmentRed": 30,
        "LuminanceAdjustmentOrange": 30,
        "LuminanceAdjustmentYellow": 30,
        "LuminanceAdjustmentGreen": 30,
        "LuminanceAdjustmentAqua": 30,
        "LuminanceAdjustmentBlue": 30,
        "LuminanceAdjustmentPurple": 30,
        "LuminanceAdjustmentMagenta": 30,
        "Sharpness": 40,
        "SharpenRadius": 2,
        "SharpenDetail": 80,
        "SharpenEdgeMasking": 50,
        "LuminanceSmoothing": 50,
        "LuminanceNoiseReductionDetail": 50,
        "LuminanceNoiseReductionContrast": 50,
        "ColorNoiseReduction": 50,
        "ColorNoiseReductionDetail": 50,
        "ColorNoiseReductionSmoothness": 50,
        "ColorGradeMidtoneHue": 40,
        "SplitToningShadowHue": 20,
        "ColorGradeShadowLum": 40,
        "ColorGradeBlending": 25,
        "SplitToningBalance": 30,
        "SplitToningHighlightHue": 30,
        "SplitToningHighlightLum": 40,
        "SplitToningShadowSaturation": 30,
        "SplitToningHighlightSaturation": 30,
        "ColorGradeMidtoneSat": 20,
        "ColorGradeGlobalHue": 20,
        "ColorGradeGlobalSat": 20,
        "ColorGradeGlobalLum": 40,
        "GrainAmount": 40,
        "GrainSize": 30,
        "GrainFrequency": 30,
        "PostCropVignetteAmount": 20,
        "PostCropVignetteMidpoint": 50,
        "PostCropVignetteFeather": 40,
        "PostCropVignetteRoundness": 50,
        "PostCropVignetteHighlightContrast": 50,
        "PostCropVignetteStyle": 1,
        "IncrementalTemperature": 30,
        "IncrementalTint": 20,
        
        # Local adjustment parameter thresholds
        "LocalExposure2012": 0.08,    # Local exposure error
        "LocalContrast2012": 0.3,     # Local contrast error
        "LocalHighlights2012": 1,   # Local highlights error
        "LocalShadows2012": 0.8,      # Local shadows error
        "LocalWhites2012": 0.15,       # Local whites error
        "LocalBlacks2012": 0.20,       # Local blacks error
        "LocalClarity": 0.3,          # Local clarity error
        "LocalClarity2012": 0.3,      # Local clarity error
        "LocalDehaze": 0.15,           # Local dehaze error
        "LocalTexture": 0.35,          # Local texture error
        "LocalHue": 0.3,              # Local hue error, range -1~1
        "LocalSaturation": 0.15,       # Local saturation error, range -1~1
        "LocalCurveRefineSaturation": 100, # Local saturation curve adjustment error
        "LocalBrightness": 10,       # Local brightness error within 10 units acceptable
        "LocalToningHue": 20,        # Local toning hue error
        "LocalToningSaturation": 0.3, # Local toning saturation error
        "LocalTemperature": 0.4,     # Local temperature error, range -1~1
        "LocalTint": 0.25,             # Local tint error, range -1~1
        "LocalLuminanceNoise": 0.45,   # Local luminance noise error
        "LocalMoire": 0.15,            # Local moire error
        "LocalDefringe": 1,         # Local defringe error
        "LocalGrain": 0.4,            # Local grain error
        "LocalSharpness": 0.2,       # Local sharpness error
        
        # Default thresholds - for unlisted parameters
        "DEFAULT_NUMERIC": 1,       # Default numeric parameter error within 1 unit acceptable
        "CorrectionAmount": 0.3,     # Mask strength error within 0.3 units acceptable
    }
    return param_thresholds.get(param_name, param_thresholds["DEFAULT_NUMERIC"])

def compare_range_masks(pred, gt):
    """Compare color range and luminance range masks"""
    # Check basic attributes
    basic_sim = compare_basic_mask_attributes(pred, gt)
    
    # Check if both have CorrectionRangeMask
    if "CorrectionRangeMask" not in pred or "CorrectionRangeMask" not in gt:
        return 0.3 * basic_sim  # If missing range info, return only part of basic attribute score
    
    pred_range = pred["CorrectionRangeMask"]
    gt_range = gt["CorrectionRangeMask"]
    
    # Check if version and type match
    if pred_range.get("Version") != gt_range.get("Version") or pred_range.get("Type") != gt_range.get("Type"):
        return 0.3 * basic_sim  # Version or type mismatch, return only basic attribute score
    
    range_type = pred_range.get("Type")
    
    # Compare color range (Type 1)
    if range_type == 1:
        # Check inversion - critical attribute
        if pred_range.get("Invert") != gt_range.get("Invert"):
            return 0.0
        
        # Calculate component similarities
        color_amount_sim = 0.0
        sample_type_sim = 1.0 if pred_range.get("SampleType") == gt_range.get("SampleType") else 0.5
        points_sim = 0.0
        
        # Check color amount
        if "ColorAmount" in pred_range and "ColorAmount" in gt_range:
            diff = abs(pred_range["ColorAmount"] - gt_range["ColorAmount"])
            color_amount_sim = max(0, 1 - diff/0.5)  # Difference above 0.5 is considered completely different
        
        # Check color point model (most complex part)
        if "PointModels" in pred_range and "PointModels" in gt_range:
            try:
                pred_points = pred_range["PointModels"][0].split(" ")
                gt_points = gt_range["PointModels"][0].split(" ")
                
                # If both have point data
                if pred_points and gt_points:
                    # Convert points to float values
                    pred_point = [float(x) for x in pred_points]
                    gt_point = [float(x) for x in gt_points]
                    
                    # Calculate Euclidean distance between points
                    color_dist = sum((p - g)**2 for p, g in zip(pred_point, gt_point)) ** 0.5
                    points_sim = max(0, 1 - color_dist/1.0)  # Distance above 1.0 is completely different
            except Exception:
                points_sim = 0.3  # Give a low score on parsing failure
        
        # Combined color range similarity: color amount(20%) + sample type(10%) + point model(70%)
        range_sim = 0.2 * color_amount_sim + 0.1 * sample_type_sim + 0.7 * points_sim
    
    # Compare luminance range (Type 2)
    elif range_type == 2:
        # Check inversion - critical attribute
        if pred_range.get("Invert") != gt_range.get("Invert"):
            return 0.0
        
        # Calculate component similarities
        sample_type_sim = 1.0 if pred_range.get("SampleType") == gt_range.get("SampleType") else 0.5
        lum_range_sim = 0.0
        depth_sim = 0.0
        
        # Check luminance range
        if "LumRange" in pred_range and "LumRange" in gt_range:
            try:
                pred_lum = [float(x) for x in pred_range["LumRange"].split()]
                gt_lum = [float(x) for x in gt_range["LumRange"].split()]
                
                # Calculate luminance range differences
                if len(pred_lum) == len(gt_lum):
                    diffs = [abs(p - g) for p, g in zip(pred_lum, gt_lum)]
                    avg_diff = sum(diffs) / len(diffs)
                    lum_range_sim = max(0, 1 - avg_diff/0.5)  # Average difference above 0.5 is completely different
            except Exception:
                lum_range_sim = 0.3  # Give a low score on parsing failure
        
        # Check depth sampling information
        if "LuminanceDepthSampleInfo" in pred_range and "LuminanceDepthSampleInfo" in gt_range:
            try:
                pred_depth = [float(x) for x in pred_range["LuminanceDepthSampleInfo"].split()]
                gt_depth = [float(x) for x in gt_range["LuminanceDepthSampleInfo"].split()]
                
                # Calculate depth information differences
                if len(pred_depth) == len(gt_depth):
                    diffs = [abs(p - g) for p, g in zip(pred_depth, gt_depth)]
                    avg_diff = sum(diffs) / len(diffs)
                    depth_sim = max(0, 1 - avg_diff/0.5)
            except Exception:
                depth_sim = 0.3  # Give a low score on parsing failure
        
        # Combined luminance range similarity: sample type(10%) + luminance range(70%) + depth info(20%)
        range_sim = 0.1 * sample_type_sim + 0.7 * lum_range_sim + 0.2 * depth_sim
    else:
        # Unknown range type
        range_sim = 0.5  # Default similarity for unknown types
    
    # Final similarity: basic attributes * range similarity
    similarity = basic_sim * range_sim
    
    return similarity

def parse_point_model(point_str):
    """Parse color point model string to numeric list"""
    try:
        values = [float(x) for x in point_str.split()]
        return values
    except Exception:
        return None


def get_param_default_value(param_name, type):
    # Return default values for various parameters
    defaults = {
            "WhiteBalance": "As Shot",
            "ParametricShadowSplit": 25,
            "ParametricMidtoneSplit": 50,
            "ParametricHighlightSplit": 75,
            "ColorGradeBlending": 50,
            "DefringePurpleHueLo": 30,
            "DefringePurpleHueHi": 70,
            "DefringeGreenHueLo": 40,
            "DefringeGreenHueHi": 60,
            "PerspectiveScale": 100,
            "ToneCurveName2012": "Linear",
            "CameraProfile": "Default Color",
    }

    # Default values by type
    type_defaults = {
        bool: True,
        int: 0,
        float: 0.0,
        str: "",
        dict: {},
    }
    return defaults.get(param_name, type_defaults.get(type))

def compare_point_colors(pred_points, gt_points):
    """Compare global PointColors parameters, supporting many-to-many matching of object lists"""
    # If prediction is None, create default points with same length as ground truth
    if pred_points is None:
        # Default point template with -1.0 values
        default_point = {
            "SrcHue": -1.0,
            "SrcSat": -1.0,
            "SrcLum": -1.0,
            "HueShift": -1.0,
            "SatScale": -1.0,
            "LumScale": -1.0,
            "RangeAmount": -1.0,
            "HueRange": {
                "LowerNone": -1.0,
                "LowerFull": -1.0,
                "UpperFull": -1.0,
                "UpperNone": -1.0
            },
            "SatRange": {
                "LowerNone": -1.0,
                "LowerFull": -1.0,
                "UpperFull": -1.0,
                "UpperNone": -1.0
            },
            "LumRange": {
                "LowerNone": -1.0,
                "LowerFull": -1.0,
                "UpperFull": -1.0,
                "UpperNone": -1.0
            }
        }
        pred_points = [default_point] * len(gt_points)

    # Early return if either list is empty
    if not pred_points or not gt_points:
        return 0.0  # If one is empty but the other is not, consider as complete mismatch
    
    # Build cost matrix - calculate similarity between each pair of color points
    cost_matrix = []
    for pred_point in pred_points:
        # Calculate similarity for each ground truth point
        similarities = [calculate_color_point_similarity(pred_point, gt_point) for gt_point in gt_points]
        # Convert to costs (1-similarity)
        cost_matrix.append([1.0 - sim for sim in similarities])
    
    # Handle empty matrix case
    if not cost_matrix:
        return 0.0
    
    # Balance the matrix for Hungarian algorithm
    similarity_threshold = 0.2
    low_similarity_cost = 0.9  # Represents low similarity but non-zero
    
    # Handle unbalanced rows and columns
    if len(pred_points) > len(gt_points):
        # More predictions than ground truth, add virtual rows
        for _ in range(len(pred_points) - len(gt_points)):
            cost_matrix.append([low_similarity_cost] * len(gt_points))
    elif len(gt_points) > len(pred_points):
        # More ground truth than predictions, add virtual columns
        for row in cost_matrix:
            row.extend([low_similarity_cost] * (len(gt_points) - len(pred_points)))
    
    # Find optimal assignment using Hungarian algorithm
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    # Calculate total similarity
    total_similarity = 0.0
    valid_matches = 0
    
    for i, j in zip(row_ind, col_ind):
        # Check if this is a valid match (not virtually added)
        if i < len(pred_points) and j < len(gt_points):
            similarity = 1.0 - cost_matrix[i][j]
            if similarity > similarity_threshold:  # Only consider matches with similarity at least 0.2
                total_similarity += similarity
                valid_matches += 1
    
    # Calculate completeness score: matches/total
    if valid_matches == 0:
        return 0.0
        
    completeness = min(
        valid_matches / max(1, len(pred_points)),
        valid_matches / max(1, len(gt_points))
    )
    
    # Final score: average similarity(70%) + completeness(30%)
    return 0.7 * (total_similarity / valid_matches) + 0.3 * completeness

def calculate_color_point_similarity(pred_point, gt_point):
    """Calculate similarity between two color points"""
    # Define field weights
    field_weights = {
        # Source color attributes (40%)
        "SrcHue": 0.15,
        "SrcSat": 0.15,
        "SrcLum": 0.10,
        # Adjustment values (40%)
        "HueShift": 0.15,
        "SatScale": 0.125,
        "LumScale": 0.125,
        "RangeAmount": 0.10,
        # Range information (20%) - calculated below
    }
    
    # Initialize total score and weight
    total_score = 0.0
    total_weight = 0.0
    
    # 1. Compare basic fields
    for field, weight in field_weights.items():
        if field in pred_point and field in gt_point:
            # Special handling for Hue fields as they are circular (0~6.28)
            if field in ("SrcHue", "HueShift"):
                # Handle cyclic nature of hue (0~6.28 corresponds to 0~360 degrees)
                diff = abs(pred_point[field] - gt_point[field])
                if diff > 3.14:  # If more than half circle, take the shorter arc
                    diff = 6.28 - diff
                # Normalize to 0~1
                field_sim = max(0, 1 - diff/1.57)  # Differences above 90 degrees (1.57 radians) considered completely different
            else:
                # Other numeric fields
                # Get typical range for this field
                field_range = get_color_point_field_range(field)
                # Calculate difference and normalize
                diff = abs(pred_point[field] - gt_point[field])
                field_sim = max(0, 1 - diff/field_range)
            
            # Add weighted score
            total_score += field_sim * weight
            total_weight += weight
    
    # 2. Compare range information (HueRange, SatRange, LumRange)
    range_weight = 0.20  # Total weight for range information
    range_fields = ["HueRange", "SatRange", "LumRange"]
    
    # Calculate average similarity across available range fields
    range_similarities = [compare_range_object(pred_point[field], gt_point[field])
                         for field in range_fields 
                         if field in pred_point and field in gt_point]
    
    # Add range score if any range fields were compared
    if range_similarities:
        avg_range_sim = sum(range_similarities) / len(range_similarities)
        total_score += avg_range_sim * range_weight
        total_weight += range_weight
    
    # Return normalized total score
    return total_score / total_weight if total_weight > 0 else 0.0

def compare_range_object(pred_range, gt_range):
    """Compare range objects (HueRange/SatRange/LumRange) similarity"""
    range_fields = ["LowerNone", "LowerFull", "UpperFull", "UpperNone"]
    
    # Check if all required fields exist
    if not all(field in pred_range and field in gt_range for field in range_fields):
        return 0.5  # Missing fields, give medium score
    
    try:
        # Calculate differences for each field
        field_diffs = [abs(float(pred_range[field]) - float(gt_range[field])) for field in range_fields]
        
        # Calculate average difference and convert to similarity
        avg_diff = sum(field_diffs) / len(field_diffs)
        max_diff_threshold = 0.5  # Differences above 0.5 considered completely different
        
        return max(0, 1 - avg_diff/max_diff_threshold)
    except (ValueError, TypeError):
        # Handle conversion errors
        return 0.5  # Return medium score on error


def get_color_point_field_range(field):
    """Get typical range for color point fields"""
    ranges = {
        "SrcHue": 6.28,       # 0~6.28 (corresponds to 0~360 degrees)
        "SrcSat": 1.0,        # 0~1
        "SrcLum": 1.0,        # 0~1
        "HueShift": 1.0,      # Typical values ±0.5
        "SatScale": 1.0,      # Typical values 0~1
        "LumScale": 1.0,      # Typical values 0~1
        "RangeAmount": 1.0,   # Typical values 0~1
        # Default range
        "DEFAULT": 1.0
    }
    return ranges.get(field, ranges["DEFAULT"])

def compare_tone_curves(pred_curve, gt_curve):
    """Compare tone curves and calculate similarity score"""
    # Handle empty curves
    if len(gt_curve) == 0:
        return 0.0, False
        
    # Use default linear curve if prediction is empty
    if len(pred_curve) == 0:
        pred_curve = {
            "1": 0,    # Start point x
            "2": 0,    # Start point y
            "3": 255,  # End point x
            "4": 255,  # End point y
        }

    # Preprocessing: extract coordinate pairs from curves
    try:
        # Extract coordinate pairs from dictionaries
        pred_points = []
        gt_points = []
        
        # Extract points from prediction curve (odd keys = x, even keys = y)
        i = 1
        while i in pred_curve and i+1 in pred_curve:
            x = float(pred_curve[i])
            y = float(pred_curve[i+1])
            pred_points.append((x, y))
            i += 2
        
        # Extract points from ground truth curve
        i = 1
        while i in gt_curve and i+1 in gt_curve:
            x = float(gt_curve[i])
            y = float(gt_curve[i+1])
            gt_points.append((x, y))
            i += 2
        
        # Need at least 2 points for interpolation
        if len(pred_points) < 2 or len(gt_points) < 2:
            return 0.0, False
        
        # Convert to numpy arrays for interpolation
        pred_x = np.array([p[0] for p in pred_points])
        pred_y = np.array([p[1] for p in pred_points])
        gt_x = np.array([p[0] for p in gt_points])
        gt_y = np.array([p[1] for p in gt_points])
        
        # Create cubic spline interpolations
        pred_cs = CubicSpline(pred_x, pred_y, bc_type='natural')
        gt_cs = CubicSpline(gt_x, gt_y, bc_type='natural')
        
        # Generate dense points for comparison
        num_samples = 500
        x_dense = np.linspace(0, 255, num_samples)
        pred_y_dense = pred_cs(x_dense)
        gt_y_dense = gt_cs(x_dense)
        
        # Calculate RMSE (Root Mean Square Error)
        rmse = np.sqrt(np.mean((pred_y_dense - gt_y_dense) ** 2))
        
        # Convert RMSE to similarity score
        # Define thresholds for scoring
        thresholds = {
            'excellent': 10,   # RMSE ≤ 10: score from 1.0 to 0.0
            'good': 20,       # RMSE ≤ 20: score from 0.0 to -0.5
            'fair': 40        # RMSE ≤ 40: score from -0.5 to -1.0
        }
        
        # Calculate similarity score based on RMSE
        if rmse <= thresholds['excellent']:
            curve_sim = 1.0 - (rmse / thresholds['excellent'])
        elif rmse <= thresholds['good']:
            curve_sim = -0.5 * (rmse - thresholds['excellent']) / (thresholds['good'] - thresholds['excellent'])
        elif rmse <= thresholds['fair']:
            curve_sim = -0.5 - 0.5 * (rmse - thresholds['good']) / (thresholds['fair'] - thresholds['good'])
        else:
            # RMSE > 40, fixed at -1.0
            curve_sim = -1.0
        
        return curve_sim, True
    except Exception as e:
        # Return low but non-zero score on parsing or comparison error
        return 0.1, False

def get_look_param_score(gt_param, pred_param):
    """Calculate similarity score for Look parameters"""
    # Early return if either parameter is None
    if gt_param is None or pred_param is None:
        return 0.0
    
    # Initialize score tracking
    total_score = 0.0
    total_count = 0
    
    # Keys to exclude from comparison
    exclude_keys = ["CompatibleVersion", "ProcessVersion"]
    
    # Special keys that need curve comparison
    curve_keys = ["ToneCurvePV2012", "ToneCurvePV2012Red", "ToneCurvePV2012Green", "ToneCurvePV2012Blue"]
    
    # Compare each parameter in ground truth
    for key in gt_param:
        # Skip excluded keys
        if key in exclude_keys:
            continue
            
        # Add to total count
        total_count += 1
        
        # If key exists in prediction
        if key in pred_param:
            # Special handling for tone curves
            if key in curve_keys:
                curve_sim, is_valid = compare_tone_curves(gt_param[key], pred_param[key])
                if is_valid:
                    total_score += curve_sim
            # Exact match for other parameters
            elif gt_param[key] == pred_param[key]:
                total_score += 1.0
        # No score for missing parameters
    
    # Return average score or 0 if no parameters were compared
    return total_score / total_count if total_count > 0 else 0.0
