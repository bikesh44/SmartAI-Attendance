import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  FaceDetector,
  FilesetResolver,
} from "@mediapipe/tasks-vision";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import {
  faCamera,
  faCameraRotate,
  faCheck,
  faCircleCheck,
  faSpinner,
  faVideo,
  faVideoSlash,
} from "@fortawesome/free-solid-svg-icons";

import "./LiveFaceCapture.css";

const MEDIAPIPE_WASM_URL =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision/wasm";

const FACE_MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite";

const REQUIRED_CAPTURE_SCORE = 90;
const CAPTURE_COUNT = 3;
const CAPTURE_INTERVAL_MS = 120;

const OVAL = {
  left: 0.28,
  top: 0.12,
  width: 0.44,
  height: 0.76,
};

function clamp(value, min = 0, max = 100) {
  return Math.min(Math.max(value, min), max);
}

function getFacePositionScore(
  boundingBox,
  videoWidth,
  videoHeight,
) {
  if (
    !boundingBox ||
    !videoWidth ||
    !videoHeight
  ) {
    return 0;
  }

  const faceLeft =
    boundingBox.originX / videoWidth;

  const faceTop =
    boundingBox.originY / videoHeight;

  const faceRight =
    (boundingBox.originX +
      boundingBox.width) /
    videoWidth;

  const faceBottom =
    (boundingBox.originY +
      boundingBox.height) /
    videoHeight;

  const faceCenterX =
    (faceLeft + faceRight) / 2;

  const faceCenterY =
    (faceTop + faceBottom) / 2;

  const faceWidth =
    faceRight - faceLeft;

  const faceHeight =
    faceBottom - faceTop;

  const ovalCenterX =
    OVAL.left + OVAL.width / 2;

  const ovalCenterY =
    OVAL.top + OVAL.height / 2;

  /*
   * ---------------------------------------------------------
   * CENTER SCORE
   * ---------------------------------------------------------
   */

  const centerDistance =
    Math.sqrt(
      Math.pow(
        (faceCenterX - ovalCenterX) /
          (OVAL.width / 2),
        2,
      ) +
        Math.pow(
          (faceCenterY - ovalCenterY) /
            (OVAL.height / 2),
          2,
        ),
    );

  const centerScore = clamp(
    100 - centerDistance * 100,
  );

  /*
   * ---------------------------------------------------------
   * SIZE SCORE
   * ---------------------------------------------------------
   */

  const targetFaceHeight =
    OVAL.height * 0.68;

  const sizeDifference =
    Math.abs(
      faceHeight - targetFaceHeight,
    ) / targetFaceHeight;

  const sizeScore = clamp(
    100 - sizeDifference * 100,
  );

  /*
   * ---------------------------------------------------------
   * BOUNDARY SCORE
   * ---------------------------------------------------------
   */

  const insideLeft =
    faceLeft >= OVAL.left;

  const insideTop =
    faceTop >= OVAL.top;

  const insideRight =
    faceRight <=
    OVAL.left + OVAL.width;

  const insideBottom =
    faceBottom <=
    OVAL.top + OVAL.height;

  const insideScore =
    insideLeft &&
    insideTop &&
    insideRight &&
    insideBottom
      ? 100
      : 45;

  /*
   * ---------------------------------------------------------
   * FACE SHAPE SCORE
   * ---------------------------------------------------------
   */

  const aspectRatio =
    faceWidth / faceHeight;

  const shapeDifference =
    Math.abs(aspectRatio - 0.72);

  const shapeScore = clamp(
    100 - shapeDifference * 180,
  );

  /*
   * ---------------------------------------------------------
   * FINAL POSITION SCORE
   * ---------------------------------------------------------
   */

  const finalScore =
    centerScore * 0.35 +
    sizeScore * 0.30 +
    insideScore * 0.25 +
    shapeScore * 0.10;

  return Math.round(
    clamp(finalScore),
  );
}

function getScoreMessage(
  score,
  faceCount,
) {
  if (faceCount === 0) {
    return "Position your face inside the oval.";
  }

  if (faceCount > 1) {
    return "Only one face should be visible.";
  }

  if (score < 50) {
    return "Move your face toward the oval.";
  }

  if (score < 75) {
    return "Move closer to the center.";
  }

  if (score < REQUIRED_CAPTURE_SCORE) {
    return "Almost there — hold still.";
  }

  return "Perfect position — capturing...";
}

function LiveFaceCapture({
  onCapture,
  onRetake,
  footerAction,
  disabled = false,
}) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const detectorRef = useRef(null);
  const animationFrameRef = useRef(null);

  const mountedRef = useRef(true);
  const detectingRef = useRef(false);

  /*
   * This lock belongs to the complete
   * three-image capture process.
   */
  const captureInProgressRef =
    useRef(false);

  const capturedFramesRef =
    useRef([]);

  const [cameraStatus, setCameraStatus] =
    useState("idle");

  const [cameraError, setCameraError] =
    useState("");

  const [faceCount, setFaceCount] =
    useState(0);

  const [faceScore, setFaceScore] =
    useState(0);

  const [captureStep, setCaptureStep] =
    useState(0);

  const [captureMessage, setCaptureMessage] =
    useState(
      "Start the camera to begin face registration.",
    );

  const [capturedImage, setCapturedImage] =
    useState(null);

  /*
   * =========================================================
   * STOP CAMERA
   * =========================================================
   */

  const stopCamera = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(
        animationFrameRef.current,
      );

      animationFrameRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current
        .getTracks()
        .forEach((track) => {
          track.stop();
        });

      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    detectingRef.current = false;

    if (mountedRef.current) {
      setCameraStatus("idle");
    }
  }, []);

  /*
   * =========================================================
   * INITIALIZE FACE DETECTOR
   * =========================================================
   */

  const initializeDetector =
    useCallback(async () => {
      if (detectorRef.current) {
        return detectorRef.current;
      }

      const vision =
        await FilesetResolver.forVisionTasks(
          MEDIAPIPE_WASM_URL,
        );

      const detector =
        await FaceDetector.createFromOptions(
          vision,
          {
            baseOptions: {
              modelAssetPath:
                FACE_MODEL_URL,
            },

            runningMode: "VIDEO",

            minDetectionConfidence: 0.5,

            minSuppressionThreshold: 0.3,
          },
        );

      detectorRef.current = detector;

      return detector;
    }, []);

  /*
   * =========================================================
   * CAPTURE ONE FRAME
   * =========================================================
   *
   * IMPORTANT:
   * This function does NOT control
   * captureInProgressRef.
   *
   * The three-frame capture process
   * controls that lock.
   * =========================================================
   */

  const captureFrame = useCallback(
    (score) => {
      const video = videoRef.current;
      const canvas = canvasRef.current;

      if (
        !video ||
        !canvas ||
        video.videoWidth === 0 ||
        video.videoHeight === 0
      ) {
        return Promise.resolve(null);
      }

      const width = video.videoWidth;
      const height = video.videoHeight;

      console.log("[FACE CAPTURE DEBUG]", {
        videoWidth: width,
        videoHeight: height,
        readyState: video.readyState,
      });

      canvas.width = width;
      canvas.height = height;

      const context =
        canvas.getContext("2d");

      if (!context) {
        return Promise.resolve(null);
      }

      /*
       * The preview is mirrored, so mirror
       * the captured image as well.
       */

      context.save();

      context.translate(width, 0);
      context.scale(-1, 1);

      context.drawImage(
        video,
        0,
        0,
        width,
        height,
      );

      context.restore();

      return new Promise((resolve) => {
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              resolve(null);
              return;
            }

            resolve({
              blob,
              score,
              createdAt: Date.now(),
            });
          },
          "image/jpeg",
          0.94,
        );
      });
    },
    [],
  );

  /*
   * =========================================================
   * COMPLETE CAPTURE PROCESS
   * =========================================================
   */

  const finishCaptureProcess =
    useCallback(() => {
      const frames =
        capturedFramesRef.current;

      if (
        frames.length !== CAPTURE_COUNT
      ) {
        return;
      }

      /*
       * Highest face-position score wins.
       */
      const bestFrame =
        [...frames].sort(
          (a, b) => b.score - a.score,
        )[0];

      const previewUrl =
        URL.createObjectURL(
          bestFrame.blob,
        );

      setCapturedImage({
        blob: bestFrame.blob,
        previewUrl,
        score: bestFrame.score,
      });

      setCaptureMessage(
        "Best face image selected.",
      );

      setFaceScore(bestFrame.score);

      setCaptureStep(
        CAPTURE_COUNT,
      );

      stopCamera();

      if (onCapture) {
        onCapture(bestFrame.blob);
      }
    }, [onCapture, stopCamera]);

  /*
   * =========================================================
   * AUTOMATIC THREE-FRAME CAPTURE
   * =========================================================
   *
   * 90%+:
   *
   * Capture 1
   *    ↓ 120ms
   * Capture 2
   *    ↓ 120ms
   * Capture 3
   *    ↓
   * Select best
   * =========================================================
   */

  const attemptAutomaticCapture =
    useCallback(
      async (score) => {
        if (
          score < REQUIRED_CAPTURE_SCORE
        ) {
          return;
        }

        /*
         * Prevent the detection loop from
         * starting another capture sequence.
         */
        if (
          captureInProgressRef.current
        ) {
          return;
        }

        /*
         * Do not capture more than three.
         */
        if (
          capturedFramesRef.current
            .length >= CAPTURE_COUNT
        ) {
          return;
        }

        captureInProgressRef.current =
          true;

        try {
          /*
           * -------------------------------------------------
           * CAPTURE 1
           * -------------------------------------------------
           */

          setCaptureMessage(
            "Face aligned — capturing 1/3...",
          );

          const firstFrame =
            await captureFrame(score);

          if (!firstFrame) {
            setCameraError(
              "Unable to capture the current camera frame.",
            );

            return;
          }

          capturedFramesRef.current.push(
            firstFrame,
          );

          setCaptureStep(1);

          /*
           * -------------------------------------------------
           * CAPTURE 2 + 3
           * -------------------------------------------------
           */

          for (
            let index = 1;
            index < CAPTURE_COUNT;
            index += 1
          ) {
            await new Promise(
              (resolve) => {
                setTimeout(
                  resolve,
                  CAPTURE_INTERVAL_MS,
                );
              },
            );

            if (!mountedRef.current) {
              return;
            }

            const frame =
              await captureFrame(score);

            if (!frame) {
              continue;
            }

            capturedFramesRef.current.push(
              frame,
            );

            const completed =
              capturedFramesRef.current
                .length;

            setCaptureStep(
              completed,
            );

            if (
              completed <
              CAPTURE_COUNT
            ) {
              setCaptureMessage(
                `Face aligned — capturing ${completed + 1}/${CAPTURE_COUNT}...`,
              );
            }
          }

          /*
           * -------------------------------------------------
           * SELECT BEST
           * -------------------------------------------------
           */

          if (
            capturedFramesRef.current
              .length === CAPTURE_COUNT
          ) {
            setCaptureMessage(
              "Selecting best image...",
            );

            finishCaptureProcess();
          }
        } catch (error) {
          console.error(
            "Automatic face capture failed:",
            error,
          );

          if (mountedRef.current) {
            setCameraError(
              "Face capture failed. Please try again.",
            );
          }
        } finally {
          captureInProgressRef.current =
            false;
        }
      },
      [captureFrame, finishCaptureProcess],
    );

  const handleManualCapture = useCallback(async () => {
    if (disabled || cameraStatus !== "active") return;
    try {
      captureInProgressRef.current = true;
      setCaptureMessage("Capturing current face frame...");
      const frame = await captureFrame(95);
      if (frame && frame.blob) {
        const previewUrl = URL.createObjectURL(frame.blob);
        setCapturedImage({
          blob: frame.blob,
          previewUrl,
          score: 95,
        });
        setFaceScore(95);
        setCaptureStep(CAPTURE_COUNT);
        stopCamera();
        if (onCapture) {
          onCapture(frame.blob);
        }
      }
    } catch (e) {
      console.error("Manual face capture failed:", e);
      setCameraError("Unable to capture frame. Please try again.");
    } finally {
      captureInProgressRef.current = false;
    }
  }, [captureFrame, disabled, cameraStatus, onCapture, stopCamera]);

  /*
   * =========================================================
   * DETECTION LOOP
   * =========================================================
   */

  const runDetection =
    useCallback(async () => {
      if (
        !mountedRef.current ||
        detectingRef.current
      ) {
        return;
      }

      const video = videoRef.current;

      const detector =
        detectorRef.current;

      if (
        !video ||
        !detector ||
        video.readyState < 2 ||
        video.videoWidth === 0
      ) {
        return;
      }

      detectingRef.current = true;

      try {
        const timestamp =
          performance.now();

        const result =
          detector.detectForVideo(
            video,
            timestamp,
          );

        const detections =
          result?.detections || [];

        const detectedCount =
          detections.length;

        if (mountedRef.current) {
          setFaceCount(
            detectedCount,
          );
        }

        /*
         * Exactly one face is required.
         */

        if (detectedCount !== 1) {
          if (mountedRef.current) {
            setFaceScore(0);

            setCaptureMessage(
              getScoreMessage(
                0,
                detectedCount,
              ),
            );
          }

          return;
        }

        const detection =
          detections[0];

        const boundingBox =
          detection?.boundingBox;

        const score =
          getFacePositionScore(
            boundingBox,
            video.videoWidth,
            video.videoHeight,
          );

        if (mountedRef.current) {
          setFaceScore(score);

          /*
           * Don't overwrite the capture
           * message while the three-photo
           * process is running.
           */
          if (
            !captureInProgressRef.current
          ) {
            setCaptureMessage(
              getScoreMessage(
                score,
                detectedCount,
              ),
            );
          }
        }

        /*
         * Once 90% is reached, start the
         * three-frame capture immediately.
         */
        if (
          !disabled &&
          cameraStatus === "active"
        ) {
          await attemptAutomaticCapture(
            score,
          );
        }
      } catch (error) {
        console.error(
          "Face detection failed:",
          error,
        );
      } finally {
        detectingRef.current = false;
      }
    }, [
      attemptAutomaticCapture,
      cameraStatus,
      disabled,
    ]);

  /*
   * =========================================================
   * DETECTION ANIMATION LOOP
   * =========================================================
   */

  useEffect(() => {
    if (
      cameraStatus !== "active"
    ) {
      return undefined;
    }

    const loop = async () => {
      await runDetection();

      if (
        mountedRef.current &&
        cameraStatus === "active"
      ) {
        animationFrameRef.current =
          requestAnimationFrame(
            loop,
          );
      }
    };

    animationFrameRef.current =
      requestAnimationFrame(loop);

    return () => {
      if (
        animationFrameRef.current
      ) {
        cancelAnimationFrame(
          animationFrameRef.current,
        );

        animationFrameRef.current =
          null;
      }
    };
  }, [
    cameraStatus,
    runDetection,
  ]);

  /*
   * =========================================================
   * START CAMERA
   * =========================================================
   */

  const startCamera = useCallback(
    async () => {
      try {
        setCameraError("");
        setCapturedImage(null);

        setFaceCount(0);
        setFaceScore(0);
        setCaptureStep(0);

        setCaptureMessage(
          "Initializing camera...",
        );

        setCameraStatus(
          "loading",
        );

        capturedFramesRef.current =
          [];

        captureInProgressRef.current =
          false;

        stopCamera();

        setCameraStatus(
          "loading",
        );

        try {
          await initializeDetector();
        } catch (detectorError) {
          console.warn("Face detector model could not be loaded; manual capture available:", detectorError);
        }

        if (
          !mountedRef.current
        ) {
          return;
        }

        const stream =
          await navigator.mediaDevices.getUserMedia(
            {
              video: {
                facingMode: "user",

                width: {
                  ideal: 1280,
                },

                height: {
                  ideal: 720,
                },
              },

              audio: false,
            },
          );

        if (
          !mountedRef.current
        ) {
          stream
            .getTracks()
            .forEach((track) => {
              track.stop();
            });

          return;
        }

        streamRef.current =
          stream;

        /*
         * The video element is rendered while
         * cameraStatus is loading.
         *
         * Wait one browser frame so React
         * has mounted the video element.
         */

        await new Promise(
          (resolve) => {
            requestAnimationFrame(
              resolve,
            );
          },
        );

        if (
          !mountedRef.current
        ) {
          return;
        }

        const video =
          videoRef.current;

        if (!video) {
          stream
            .getTracks()
            .forEach((track) => {
              track.stop();
            });

          streamRef.current =
            null;

          throw new Error(
            "Camera video element was not available after initialization.",
          );
        }

        video.srcObject =
          stream;

        await video.play();

        if (
          !mountedRef.current
        ) {
          return;
        }

        setCameraStatus(
          "active",
        );

        setCaptureMessage(
          "Move your face inside the oval.",
        );
      } catch (error) {
        console.error(
          "Camera initialization error:",
          error,
        );

        if (
          !mountedRef.current
        ) {
          return;
        }

        if (
          error?.name ===
          "NotAllowedError"
        ) {
          setCameraError(
            "Camera permission was denied. Please allow camera access and try again.",
          );
        } else if (
          error?.name ===
          "NotFoundError"
        ) {
          setCameraError(
            "No camera was found on this device.",
          );
        } else if (
          error?.name ===
          "NotReadableError"
        ) {
          setCameraError(
            "The camera is already being used by another application.",
          );
        } else if (
          error?.name ===
          "OverconstrainedError"
        ) {
          setCameraError(
            "The requested camera settings are not supported.",
          );
        } else {
          setCameraError(
            error?.message ||
              "Camera preview could not be initialized.",
          );
        }

        setCameraStatus(
          "error",
        );
      }
    },
    [
      initializeDetector,
      stopCamera,
    ],
  );

  /*
   * =========================================================
   * RETAKE
   * =========================================================
   */

  const retakePhoto = useCallback(
    () => {
      if (
        capturedImage?.previewUrl
      ) {
        URL.revokeObjectURL(
          capturedImage.previewUrl,
        );
      }

      setCapturedImage(null);

      capturedFramesRef.current =
        [];

      captureInProgressRef.current =
        false;

      setCaptureStep(0);
      setFaceScore(0);
      setFaceCount(0);

      setCameraError("");

      setCaptureMessage(
        "Position one face inside the oval.",
      );

      // Clear the parent form's Blob too, so an old image
      // cannot be submitted after the user chooses Retake.
      onCapture?.(null);
      onRetake?.();

      startCamera();
    },
    [
      capturedImage,
      onCapture,
      onRetake,
      startCamera,
    ],
  );

  /*
   * =========================================================
   * CLEANUP
   * =========================================================
   */

  useEffect(() => {
    mountedRef.current = true;

    const videoElement =
      videoRef.current;

    return () => {
      mountedRef.current =
        false;

      if (
        animationFrameRef.current
      ) {
        cancelAnimationFrame(
          animationFrameRef.current,
        );

        animationFrameRef.current =
          null;
      }

      if (
        streamRef.current
      ) {
        streamRef.current
          .getTracks()
          .forEach((track) => {
            track.stop();
          });

        streamRef.current =
          null;
      }

      if (videoElement) {
        videoElement.srcObject =
          null;
      }

      if (
        capturedImage?.previewUrl
      ) {
        URL.revokeObjectURL(
          capturedImage.previewUrl,
        );
      }

      if (
        detectorRef.current
      ) {
        detectorRef.current.close();

        detectorRef.current =
          null;
      }
    };
  }, [capturedImage]);

  /*
   * =========================================================
   * RENDER
   * =========================================================
   */

  const scoreReady =
    faceScore >=
      REQUIRED_CAPTURE_SCORE &&
    faceCount === 1;

  return (
    <div className="live-face-capture">
      <canvas
        ref={canvasRef}
        style={{
          display: "none",
        }}
      />

      {(cameraStatus === "loading" ||
        cameraStatus === "active") &&
        !capturedImage && (
          <div className="live-face-camera">
            <video
              ref={videoRef}
              className="live-face-video"
              autoPlay
              muted
              playsInline
            />

            <div
              className={`live-face-overlay ${
                scoreReady
                  ? "live-face-overlay-ready"
                  : ""
              }`}
            >
              <div className="live-face-oval" />

              <div className="live-face-score">
                <strong>
                  {faceScore}%
                </strong>

                <span>
                  {faceCount === 1
                    ? "Face position"
                    : "Face detection"}
                </span>
              </div>
            </div>

            <div className="live-face-camera-status">
              <span
                className={
                  scoreReady
                    ? "live-face-status-ready"
                    : ""
                }
              />

              {captureMessage}
            </div>

            <div className="live-face-capture-progress">
              {Array.from({
                length:
                  CAPTURE_COUNT,
              }).map(
                (_, index) => (
                  <span
                    key={index}
                    className={
                      index <
                      captureStep
                        ? "completed"
                        : ""
                    }
                  >
                    {index <
                    captureStep ? (
                      <FontAwesomeIcon
                        icon={
                          faCircleCheck
                        }
                      />
                    ) : (
                      index + 1
                    )}
                  </span>
                ),
              )}
            </div>

            <div style={{ display: "flex", justifyContent: "center", marginTop: "12px", width: "100%" }}>
              <button
                type="button"
                className="live-face-start-button"
                style={{ padding: "8px 18px", fontSize: "12px", width: "auto" }}
                onClick={handleManualCapture}
                disabled={disabled}
              >
                <FontAwesomeIcon icon={faCamera} />
                Capture Now
              </button>
            </div>
          </div>
        )}

      {capturedImage && (
        <div className="live-face-preview">
          <div className="live-face-preview-image">
            <img
              src={
                capturedImage.previewUrl
              }
              alt="Best captured face preview"
            />

            <div className="live-face-best-badge">
              <FontAwesomeIcon
                icon={faCheck}
              />

              Best capture
            </div>
          </div>

          <div className="live-face-preview-status">
            <FontAwesomeIcon
              icon={faCheck}
            />

            <span>
              Best face image selected
            </span>

            <strong>
              {capturedImage.score}%
            </strong>
          </div>

          <div className="live-face-preview-actions">
            <button
              type="button"
              className="live-face-retake-button"
              onClick={retakePhoto}
              disabled={disabled}
            >
              <FontAwesomeIcon icon={faCameraRotate} />
              Retake
            </button>

            {footerAction}
          </div>
        </div>
      )}

      {cameraStatus !== "active" &&
        !capturedImage && (
          <div className="live-face-start">
            <div className="live-face-start-icon">
              <FontAwesomeIcon
                icon={
                  cameraStatus ===
                  "loading"
                    ? faSpinner
                    : faVideo
                }
                spin={
                  cameraStatus ===
                  "loading"
                }
              />
            </div>

            <h3>
              Live Face Registration
            </h3>

            <p>
              Position exactly one face
              inside the oval. The system
              will automatically capture
              three good frames and keep
              the best one.
            </p>

            <button
              type="button"
              className="live-face-start-button"
              onClick={startCamera}
              disabled={disabled}
            >
              <FontAwesomeIcon
                icon={
                  cameraStatus ===
                  "loading"
                    ? faSpinner
                    : faCamera
                }
                spin={
                  cameraStatus ===
                  "loading"
                }
              />

              {cameraStatus ===
              "loading"
                ? "Starting Camera..."
                : "Start Camera"}
            </button>
          </div>
        )}

      {cameraStatus === "error" && (
        <div className="live-face-error">
          <FontAwesomeIcon
            icon={faVideoSlash}
          />

          <span>
            {cameraError}
          </span>
        </div>
      )}
    </div>
  );
}

export default LiveFaceCapture;