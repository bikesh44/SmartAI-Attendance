# Recognition Threshold

## Purpose

This document records the initial experimental threshold used by the Computer Vision recognition service.

The threshold is used by `FaceService.recognize_student()` to determine whether the best cosine similarity score is sufficient to recognize a registered student.

The current threshold is an initial experimental value and must not be considered a permanently finalized production threshold.

## Similarity Metric

The recognition service uses cosine similarity between the probe face feature and a registered student's face feature.

Higher cosine similarity indicates a stronger similarity between the two face feature vectors.

The recognition decision is made using:
```python
best_similarity >= similarity_threshold
```
## Experimental Results
### Same-Person Comparisons

| Comparison                         | Cosine Similarity | L2 Distance|
| Person A image 1 ↔ Person A image 2| 0.6955            | 0.7804     |
| Person B image 1 ↔ Person B image 2| 0.5591            | 0.9391     |

Same-person similarity range:
- Minimum: `0.5591`
- Maximum: `0.6955`

### Different-Person Comparisons

| Comparison                          | Cosine Similarity | L2 Distance |
|-------------------------------------|-------------------|-------------|
| Person A image 1 ↔ Person B image 1 | 0.4574            | 1.0417      |
| Person A image 1 ↔ Person B image 2 | 0.5139            | 0.9860      |
| Person A image 2 ↔ Person B image 1 | 0.3295            | 1.1580      |
| Person A image 2 ↔ Person B image 2 | 0.4529            | 1.046       |

Different-person similarity range:
- Minimum: `0.3295`
- Maximum: `0.5139`

## Current Experimental Threshold

The current initial threshold is:
```text
0.54
```
The threshold was selected because it lies between the highest observed different-person similarity score and the lowest observed same-person similarity score.

Highest observed different-person score:
```text
0.5139
```

Initial experimental threshold:
```text
0.5400
```

Lowest observed same-person score:
```text
0.5591
```

The current experimental results therefore show a separation between the observed same-person and different-person similarity scores.

## Recognition Decision
The recognition service uses the threshold as follows:
```python
if best_similarity >= similarity_threshold:
    # recognized
else:
    # not recognized
```

With the current threshold:
```python
similarity_threshold = 0.54
```

Examples from the current test results:

- `0.6955` → recognized
- `0.5591` → recognized
- `0.5139` → not recognized
- `0.4711` → not recognized

## Threshold Limitation

The threshold of `0.54` is an initial experimental value based on a small test dataset.

It must not be considered a final production threshold.

Further validation is required using a larger dataset containing:

- Multiple students.
- Multiple images per student.
- Different lighting conditions.
- Different face orientations.
- Different camera distances.
- Different image qualities.
- Additional same-person comparisons.
- Additional different-person comparisons.

Future testing should measure false acceptance and false rejection cases before the threshold is finalized for production use.

## Future Threshold Validation
The threshold should be reevaluated as the recognition dataset grows.

Future validation should compare:
- Genuine same-person similarity scores.
- Different-person similarity scores.
- False acceptance cases.
- False rejection cases.

The final production threshold should be selected only after sufficient validation data has been collected.
