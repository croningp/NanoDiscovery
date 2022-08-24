"""
.. module:: CameraControl
    :platform: Unix
    :synopsis: Module for interfacing with attached Webcams

.. moduleauthor:: Graham Keenan <https://github.com/ShinRa26>

"""

import cv2
import time

class CameraDriver:
    """
    Class for controling the camera attached to the platform
    Allows for recording of a video and taking an image
    """

    def __init__(self, config: dict):
        self.config = config

    def record_video(self, save_loc: str, duration: float, fps: int = 30):
        """
        Records a video to file

        Args:
            save_loc (str): path to save the video
            duration (int/float): Duration of the video
            fps (int): Frames per second of recording.
        """
        cap = cv2.VideoCapture(self.config["device"])
        cap.set(cv2.CAP_PROP_AUTOFOCUS, self.config["focus_auto"])
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter(save_loc, fourcc, fps, (640, 480))

        curr_time = time.time()

        while cap.isOpened():
            if time.time() > curr_time + duration:
                break
            ret, frame = cap.read()
            if ret:
                out.write(frame)
                cv2.imshow("Frame", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            else:
                break

        cap.release()
        out.release()
        cv2.destroyAllWindows()

    def take_image(self, save_loc: str):
        """
        Takes an image and saves it to file

        Args:
            save_loc (str): Path to save the image
        """
        cap = cv2.VideoCapture(0)
        _, image = cap.read()
        cv2.imwrite(save_loc, image)
        cap.release()
