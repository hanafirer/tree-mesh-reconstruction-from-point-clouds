import argparse
import numpy as np
import open3d as o3d


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--xyz", required=True)
    args = parser.parse_args()

    points = np.loadtxt(args.xyz)

    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("XYZ file must have exactly 3 columns: x y z")

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)

    print(f"Loaded {len(points)} points from {args.xyz}")
    o3d.visualization.draw_geometries([pcd])


if __name__ == "__main__":
    main()