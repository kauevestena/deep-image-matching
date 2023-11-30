from importlib import import_module

from src.deep_image_matching import logger, timer
from src.deep_image_matching.image_matching import ImageMatching
from src.deep_image_matching.io.h5_to_db import export_to_colmap
from src.deep_image_matching.parser import parse_config


def main():
    # Parse arguments
    config = parse_config()
    imgs_dir = config["general"]["image_dir"]
    output_dir = config["general"]["output_dir"]
    matching_strategy = config["general"]["matching_strategy"]
    retrieval_option = config["general"]["retrieval"]
    pair_file = config["general"]["pair_file"]
    overlap = config["general"]["overlap"]
    upright = config["general"]["upright"]
    extractor = config["extractor"]["name"]
    matcher = config["matcher"]["name"]

    # Initialize ImageMatching class
    img_matching = ImageMatching(
        imgs_dir=imgs_dir,
        output_dir=output_dir,
        matching_strategy=matching_strategy,
        retrieval_option=retrieval_option,
        local_features=extractor,
        matching_method=matcher,
        pair_file=pair_file,
        custom_config=config,
        overlap=overlap,
    )

    # Generate pairs to be matched
    pair_path = img_matching.generate_pairs()
    timer.update("generate_pairs")

    # Try to rotate images so they will be all "upright", useful for deep-learning approaches that usually are not rotation invariant
    if upright:
        img_matching.rotate_upright_images()
        timer.update("rotate_upright_images")

    # Extract features
    feature_path = img_matching.extract_features()
    timer.update("extract_features")

    # Matching
    match_path = img_matching.match_pairs(feature_path)
    timer.update("matching")

    # Features are extracted on "upright" images, this function report back images on their original orientation
    if upright:
        img_matching.rotate_back_features(feature_path)
        timer.update("rotate_back_features")

    # Export in colmap format
    database_path = output_dir / "database.db"
    export_to_colmap(
        img_dir=imgs_dir,
        feature_path=feature_path,
        match_path=match_path,
        database_path=database_path,
        camera_model="simple-radial",
        single_camera=True,
    )
    timer.update("export_to_colmap")

    # Try to run reconstruction with pycolmap
    if not config["general"]["skip_reconstruction"]:
        use_pycolmap = True
        try:
            pycolmap = import_module("pycolmap")
        except ImportError:
            logger.error("Pycomlap is not available, skipping reconstruction")
            use_pycolmap = False

    if use_pycolmap:
        from deep_image_matching import reconstruction

        # Define database path and camera mode
        database = output_dir / "database_pycolmap.db"

        # Define how pycolmap create the cameras. Possible CameraMode are:
        # CameraMode.AUTO: infer the camera model based on the image exif
        # CameraMode.PER_FOLDER: create a camera for each folder in the image directory
        # CameraMode.PER_IMAGE: create a camera for each image in the image directory
        # CameraMode.SINGLE: create a single camera for all images
        camera_mode = pycolmap.CameraMode.AUTO

        # Optional - You can manually define the cameras parameters (refer to https://github.com/colmap/colmap/blob/main/src/colmap/sensor/models.h).
        # Note, that the cameras previously detected in AUTO mode will be overwitten. Therefore, you must provide the same number of cameras and with the same order in which the cameras appear in the COLMAP database.
        # To see the camera number and order, you can run the reconstruction a first time with the AUTO camera mode (and without manually define the cameras) and then access to the database with the following code:
        # print(model.cameras)
        #
        # cam1 = pycolmap.Camera(
        #     model="SIMPLE_PINHOLE",
        #     width=6012,
        #     height=4008,
        #     params=[9.267, 3.053, 1.948],
        # )
        # cam2 = pycolmap.Camera(
        #     model="SIMPLE_PINHOLE",
        #     width=6012,
        #     height=4008,
        #     params=[6.621, 3.013, 1.943],
        # )
        # cameras = [cam1, cam2]
        cameras = None

        # Optional - You can specify some reconstruction configuration
        # options = (
        #     {
        #         "ba_refine_focal_length": False,
        #         "ba_refine_principal_point": False,
        #         "ba_refine_extra_params": False,
        #     },
        # )
        options = {}

        # Run reconstruction
        model = reconstruction.main(
            database=database,
            image_dir=imgs_dir,
            feature_path=feature_path,
            match_path=match_path,
            pair_path=pair_path,
            output_dir=output_dir,
            camera_mode=camera_mode,
            cameras=cameras,
            skip_geometric_verification=True,
            options=options,
            verbose=False,  # config["general"]["verbose"],
        )

        timer.update("pycolmap reconstruction")

    # Export in Bundler format for Metashape using colmap CLI
    # if not use_pycolmap:

    #     def export_to_bundler(
    #         database: Path, image_dir: Path, output_dir: Path, out_name: str = "bundler"
    #     ) -> bool:
    #         import subprocess
    #         from pprint import pprint

    #         colamp_path = "colmap"

    #         cmd = [
    #             colamp_path,
    #             "model_converter",
    #             "--input_path",
    #             str(database.parent.resolve()),
    #             "--output_path",
    #             str(database.parent.resolve() / out_name),
    #             "--output_type",
    #             "Bundler",
    #         ]
    #         ret = subprocess.run(cmd, capture_output=True)
    #         if ret.returncode != 0:
    #             logger.error("Unable to export to Bundler format")
    #             pprint(ret.stdout.decode("utf-8"))
    #             return False

    #         shutil.copytree(image_dir, output_dir / "images", dirs_exist_ok=True)
    #         logger.info("Export to Bundler format completed successfully")

    #         return True

    #     out_name = "bundler"
    #     export_to_bundler(database, imgs_dir, output_dir, out_name)

    timer.print("Deep Image Matching")


if __name__ == "__main__":
    main()
