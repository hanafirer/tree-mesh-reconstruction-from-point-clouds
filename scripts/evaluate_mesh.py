import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import trimesh
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt


def load_and_sample_mesh(mesh_path: Path, n_points: int) -> np.ndarray:
    print(f"Reading mesh: {mesh_path}")

    mesh = trimesh.load(mesh_path, force="mesh")

    if mesh.is_empty:
        raise ValueError(f"Mesh is empty or could not be read: {mesh_path}")

    print(f"Vertices: {len(mesh.vertices)}")
    print(f"Faces: {len(mesh.faces)}")

    print(f"Sampling {n_points} points...")
    points, _ = trimesh.sample.sample_surface(mesh, n_points)

    return np.asarray(points)

# Check which axis is the vertical 
# Assumption: horizontal axes are roughly centered around 0, vertical axis starts close to 0 and goes upward
def infer_up_axis(points: np.ndarray, tolerance: float = 0.05) -> int:
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    sizes = maxs - mins
    scores = []

    for axis in range(3):
        min_value = mins[axis]
        max_value = maxs[axis]
        size = sizes[axis]

        # Good vertical axis: minimum is close to 0 and most values are positive
        score = abs(min_value)

        # Penalize axes that go significantly below zero
        if min_value < -tolerance * max(size, 1e-8):
            score += abs(min_value) * 10.0

        # Penalize axes that do not extend upward much
        if max_value <= 0:
            score += 1000.0

        scores.append(score)

    return int(np.argmin(scores))

# Automatically convert Y-up point clouds to Z-up if needed
def ensure_z_up(points: np.ndarray, name: str = "point cloud") -> np.ndarray:
    up_axis = infer_up_axis(points)

    axis_names = ["X", "Y", "Z"]
    print(f"{name}: inferred up axis = {axis_names[up_axis]}")

    if up_axis == 2:
        print(f"{name}: already Z-up, no conversion needed.")
        return points

    if up_axis == 1:
        print(f"{name}: converting Y-up to Z-up.")
        return points[:, [0, 2, 1]]

    if up_axis == 0:
        print(f"{name}: converting X-up to Z-up.")
        return points[:, [1, 2, 0]]

    return points

# For each point in source, find the distance to the nearest point in target
# KD-tree is a special data structure used for efficient nearest neighbor searches
def nearest_neighbor_distances(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    tree = cKDTree(target)
    distances, _ = tree.query(source, k=1)
   
    return distances


# Save a colored point cloud as PLY
# Points with larger nearest-neighbor error are colored closer to red
def save_error_heatmap(points: np.ndarray, distances: np.ndarray, out_path: Path, max_distance: float = 0.20):
    out_path.parent.mkdir(parents=True, exist_ok=True)

    normalized = np.clip(distances / max_distance, 0.0, 1.0)
    colors = plt.cm.jet(normalized)[:, :3]  # RGB, values 0..1

    cloud = trimesh.points.PointCloud(points, colors=(colors * 255).astype(np.uint8))
    cloud.export(out_path)

    print(f"Saved error heatmap to: {out_path}")


# Approximate volume/surface overlap using occupied voxels
# It computes IoU between voxel cells occupied by sampled GT and prediction points
def compute_voxel_iou(gt_points: np.ndarray, pred_points: np.ndarray, voxel_size: float = 0.10) -> float:
    all_points = np.vstack([gt_points, pred_points])
    origin = all_points.min(axis=0)

    gt_voxels = np.floor((gt_points - origin) / voxel_size).astype(np.int64)
    pred_voxels = np.floor((pred_points - origin) / voxel_size).astype(np.int64)

    gt_set = set(map(tuple, gt_voxels))
    pred_set = set(map(tuple, pred_voxels))

    intersection = len(gt_set.intersection(pred_set))
    union = len(gt_set.union(pred_set))

    if union == 0:
        return 0.0
    
    return float (intersection / union)


def compute_metrics(pred_points: np.ndarray, gt_points: np.ndarray, threshold: float) -> dict:
    # Chamfer distance is the average of the nearest neighbor distances in both directions
    dist_pred_to_gt = nearest_neighbor_distances(pred_points, gt_points)
    dist_gt_to_pred = nearest_neighbor_distances(gt_points, pred_points)

    chamfer = np.mean(dist_pred_to_gt) + np.mean(dist_gt_to_pred)
    hausdorff = float(max(np.max(dist_gt_to_pred), np.max(dist_pred_to_gt)))

    # precision -> how much of the predicted points are close to the ground truth
    precision = np.mean(dist_pred_to_gt < threshold)

    # recall -> how much of the ground truth points are correctly predicted
    recall = np.mean(dist_gt_to_pred < threshold)

    # F-score -> combines recall and precision into one number
    if precision + recall == 0:
        f_score = 0.0
    else:
        f_score = (2 * precision * recall) / (precision + recall)

    metrics = {
        "chamfer_distance": float(chamfer),
        "hausdorff_distance": float(hausdorff),
        "precision": float(precision),
        "recall": float(recall),
        "f_score": float(f_score),
        "mean_dist_pred_to_gt": float(np.mean(dist_pred_to_gt)),
        "mean_dist_gt_to_pred": float(np.mean(dist_gt_to_pred)),
        "max_dist_pred_to_gt": float(np.max(dist_pred_to_gt)),
        "max_dist_gt_to_pred": float(np.max(dist_gt_to_pred)),
    }

    return metrics, dist_gt_to_pred, dist_pred_to_gt


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate reconstructed mesh against ground truth mesh."
    )

    parser.add_argument("--gt", required=True, help="Ground truth OBJ mesh")
    parser.add_argument("--pred", required=True, help="Predicted/reconstructed OBJ mesh")
    parser.add_argument("--points", type=int, default=50000, help="Number of sampled points")
    parser.add_argument("--f-threshold", type=float, default=0.05, help="Distance threshold for precision/recall/F-score, in model units. If units are meters, 0.05 = 5 cm")
    parser.add_argument("--out", default=None, help="Optional output CSV path")
    parser.add_argument("--heatmap-out", default=None, help="Optional output PLY path for GT-to-pred error heatmap")
    parser.add_argument("--heatmap-max-distance", type=float, default=0.20, help="Distance value used for heatmap color saturation")
    parser.add_argument("--voxel-size", type=float, default=0.10, help="Voxel size for approximate voxel IoU. In meters, 0.10 means 10 cm")
    args = parser.parse_args()

    gt_path = Path(args.gt)
    pred_path = Path(args.pred)

    if not gt_path.exists():
        raise FileNotFoundError(f"Ground truth mesh does not exist: {gt_path}")

    if not pred_path.exists():
        raise FileNotFoundError(f"Predicted mesh does not exist: {pred_path}")

    gt_points = load_and_sample_mesh(gt_path, args.points)
    pred_points = load_and_sample_mesh(pred_path, args.points)

    gt_points = ensure_z_up(gt_points, "ground truth")
    pred_points = ensure_z_up(pred_points, "prediction")

    metrics, dist_gt_to_pred, dist_pred_to_gt = compute_metrics(pred_points, gt_points, args.f_threshold)
    voxel_iou = compute_voxel_iou(gt_points, pred_points, voxel_size=args.voxel_size)

    metrics["voxel_iou"] = voxel_iou
    metrics["voxel_size"] = args.voxel_size

    print("Evaluation Metrics:")
    for metric, value in metrics.items():
        print(f"  {metric}: {value:.6f}")

    if args.heatmap_out is not None:
        save_error_heatmap(gt_points, dist_gt_to_pred, Path(args.heatmap_out), max_distance=args.heatmap_max_distance)

    if args.out is not None:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        row = {
            "gt_mesh": str(gt_path),
            "pred_mesh": str(pred_path),
            "sampled_points": args.points,
            "f_threshold": args.f_threshold,
            **metrics 
        }

        df = pd.DataFrame([row])
        df.to_csv(out_path, index=False)


if __name__ == "__main__":
    main()