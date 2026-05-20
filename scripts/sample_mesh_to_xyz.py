import argparse
from pathlib import Path
import numpy as np
import open3d as o3d


def sample_mesh(mesh_path: Path, number_of_points: int) -> np.ndarray:
    print(f"Reading mesh: {mesh_path}")

    mesh = o3d.io.read_triangle_mesh(str(mesh_path))

    if mesh.is_empty():
        raise ValueError(
            f"Mesh is empty or could not be read: {mesh_path}\n"
            "Check that the OBJ is a triangulated mesh and contains face data."
        )

    mesh.compute_vertex_normals()

    print(f"Sampling {number_of_points} points...")
    point_cloud = mesh.sample_points_uniformly(number_of_points=number_of_points)

    points = np.asarray(point_cloud.points)

    if points.shape[0] == 0:
        raise ValueError("No points were sampled from the mesh.")

    return points


def convert_y_up_to_z_up(points: np.ndarray) -> np.ndarray:
    """
    Blender OBJ export can produce Y-up coordinates.
    For AdTree, we want Z-up coordinates.

    Current: x, y_up, z
    Desired: x, y, z_up

    So we swap Y and Z:
    x, y, z -> x, z, y
    """
    return points[:, [0, 2, 1]]


def print_stats(points: np.ndarray) -> None:
    min_xyz = points.min(axis=0)
    max_xyz = points.max(axis=0)
    size_xyz = max_xyz - min_xyz
    center_xyz = points.mean(axis=0)

    print()
    print("Point cloud stats:")
    print(f"points: {len(points)}")
    print(f"min:    {min_xyz}")
    print(f"max:    {max_xyz}")
    print(f"size:   {size_xyz}")
    print(f"center: {center_xyz}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Sample an OBJ mesh into an XYZ point cloud for AdTree."
    )

    parser.add_argument(
        "--mesh",
        required=True,
        help="Input OBJ ground truth mesh",
    )

    parser.add_argument(
        "--out",
        required=True,
        help="Output XYZ point cloud",
    )

    parser.add_argument(
        "--points",
        type=int,
        default=50000,
        help="Number of sampled points",
    )

    parser.add_argument(
        "--no-axis-fix",
        action="store_true",
        help="Do not convert Blender Y-up coordinates to Z-up.",
    )

    args = parser.parse_args()

    mesh_path = Path(args.mesh)
    output_path = Path(args.out)

    if not mesh_path.exists():
        raise FileNotFoundError(f"Input mesh does not exist: {mesh_path}")

    points = sample_mesh(mesh_path, args.points)

    if args.no_axis_fix:
        print("Axis fix disabled. Saving coordinates as sampled.")
    else:
        print("Converting Y-up to Z-up...")
        points = convert_y_up_to_z_up(points)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Saving XYZ: {output_path}")
    np.savetxt(output_path, points, fmt="%.6f")

    print_stats(points)

    print("Done.")
    print(f"Saved {points.shape[0]} points to {output_path}")


if __name__ == "__main__":
    main()