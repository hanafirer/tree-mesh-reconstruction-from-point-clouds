import argparse
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()

    for file in args.files:
        pts = np.loadtxt(file)

        min_xyz = pts.min(axis=0)
        max_xyz = pts.max(axis=0)
        size_xyz = max_xyz - min_xyz
        center = pts.mean(axis=0)

        print()
        print(file)
        print(f"points: {len(pts)}")
        print(f"min:    {min_xyz}")
        print(f"max:    {max_xyz}")
        print(f"size:   {size_xyz}")
        print(f"center: {center}")


if __name__ == "__main__":
    main()