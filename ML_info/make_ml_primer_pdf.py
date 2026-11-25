#!/usr/bin/env python3
"""Build 'ML_Primer_for_Beginners.pdf' in ML_info/ — a plain-language,
illustrated, beginner ML primer (self-contained, no helper files).

Run the illustrations first, then this:
    python ML_info/make_illustrations.py
    python ML_info/make_ml_primer_pdf.py
"""

import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "img")

ACCENT = colors.HexColor("#1f6feb")
ACCENT_DARK = colors.HexColor("#0b3d91")
LIGHT = colors.HexColor("#eef4ff")
GREY = colors.HexColor("#555555")
CODE_BG = colors.HexColor("#f3f4f6")
AMBER_BG = colors.HexColor("#fff7e6")
GREEN = colors.HexColor("#1a7f37")

styles = getSampleStyleSheet()


def s(name, **kw):
    return ParagraphStyle(name, parent=styles["BodyText"], **kw)


TITLE = s("Title", fontName="Helvetica-Bold", fontSize=25, leading=31,
          textColor=ACCENT_DARK, alignment=TA_CENTER, spaceAfter=6)
SUBTITLE = s("Subtitle", fontName="Helvetica", fontSize=12.5, leading=17,
             textColor=GREY, alignment=TA_CENTER, spaceAfter=4)
H1 = s("H1", fontName="Helvetica-Bold", fontSize=15.5, leading=20,
       textColor=ACCENT_DARK, spaceBefore=12, spaceAfter=6)
H2 = s("H2", fontName="Helvetica-Bold", fontSize=12, leading=15.5,
       textColor=ACCENT, spaceBefore=8, spaceAfter=3)
BODY = s("Body", fontName="Helvetica", fontSize=10.2, leading=14.5,
         alignment=TA_JUSTIFY, spaceAfter=6)
BULLET = s("Bullet", fontName="Helvetica", fontSize=10.2, leading=14,
           alignment=TA_LEFT)
SMALL = s("Small", fontName="Helvetica-Oblique", fontSize=8.5, leading=11,
          textColor=GREY)
CALL = s("Call", fontName="Helvetica", fontSize=9.8, leading=13.5,
         textColor=colors.HexColor("#7a4a00"))
CALLH = s("CallH", fontName="Helvetica-Bold", fontSize=9.8, leading=13,
          textColor=colors.HexColor("#7a4a00"))
EX = s("Ex", fontName="Helvetica", fontSize=9.8, leading=13.5,
       textColor=colors.HexColor("#0b3d91"))
CODE = s("Code", fontName="Courier", fontSize=8.8, leading=11.8,
         textColor=colors.HexColor("#111111"))


def P(t, st=BODY):
    return Paragraph(t, st)


def bullets(items, st=BULLET):
    return ListFlowable(
        [ListItem(P(i, st), leftIndent=12, value="circle") for i in items],
        bulletType="bullet", start="\u2022", leftIndent=16, bulletFontSize=8,
        spaceBefore=2, spaceAfter=6,
    )


def callout(title, text, bg=AMBER_BG, edge="#e0a800"):
    inner = [P("<b>%s</b>" % title, CALLH), P(text, CALL)]
    t = Table([[inner]], colWidths=[165 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(edge)),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return KeepTogether([t, Spacer(1, 8)])


def worked(title, lines):
    """A light-blue 'worked example' box."""
    inner = [P("<b>%s</b>" % title, s("exh", fontName="Helvetica-Bold",
                                      fontSize=9.8, leading=13,
                                      textColor=colors.HexColor("#0b3d91")))]
    inner += [P(l, EX) for l in lines]
    t = Table([[inner]], colWidths=[165 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.6, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return KeepTogether([t, Spacer(1, 8)])


def code_block(lines):
    esc = "<br/>".join(
        l.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        for l in lines
    )
    t = Table([[P(esc, CODE)]], colWidths=[165 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#d0d7de")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return KeepTogether([t, Spacer(1, 8)])


def figure(name, caption, width_mm=150):
    path = os.path.join(IMG, name)
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w, h = im.size
    width = width_mm * mm
    height = width * h / w
    img = Image(path, width=width, height=height)
    cap = P(caption, s("cap", fontName="Helvetica-Oblique", fontSize=8.8,
                       leading=11.5, textColor=GREY, alignment=TA_CENTER))
    return KeepTogether([img, Spacer(1, 2), cap, Spacer(1, 10)])


def table(data, col_widths, header=True, font_size=9.3):
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d1d9")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle(style))
    return KeepTogether([t, Spacer(1, 8)])


def hr():
    return HRFlowable(width="100%", thickness=0.8,
                      color=colors.HexColor("#c9d1d9"),
                      spaceBefore=4, spaceAfter=8)


story = []

# ---------------------------------------------------------------- COVER
story.append(Spacer(1, 36 * mm))
story.append(P("Machine Learning, Explained Simply", TITLE))
story.append(P("A picture-first primer for curious beginners", SUBTITLE))
story.append(P("Read this before diving into deep learning", SUBTITLE))
story.append(Spacer(1, 6 * mm))
story.append(HRFlowable(width="60%", thickness=1.2, color=ACCENT, hAlign="CENTER"))
story.append(Spacer(1, 6 * mm))
story.append(P("Examples are taken from a real project: a motor that tells you "
               "it is getting sick \u2014 <b>motor-health-edge-ai</b>",
               s("cv", fontName="Helvetica", fontSize=10.5, leading=16,
                 textColor=ACCENT_DARK, alignment=TA_CENTER)))
story.append(Spacer(1, 12 * mm))
story.append(callout(
    "How to read this",
    "No maths background needed. Each idea gets a plain-language explanation, a "
    "picture, and \u2014 where it helps \u2014 two worked examples: one from the "
    "motor project and one everyday example. Go in order; each chapter builds on "
    "the previous one. A full glossary is at the end."))
story.append(Spacer(1, 4 * mm))
story.append(P("Companion document: <b>ML_Guide_for_Motor_Health.pdf</b> "
               "(repo root) shows how this project applies everything.",
               s("cmp", fontName="Helvetica-Oblique", fontSize=9, leading=12,
                 textColor=GREY, alignment=TA_CENTER)))
story.append(PageBreak())

# ================================================================ BODY

# ---------------------------------------------------------------- CONTENTS
story.append(P("What's inside", H1))
story.append(hr())
toc = [
    ("1", "What is machine learning?", "A machine finds rules instead of you writing them"),
    ("2", "Learning by example: the training loop", "Predict \u2192 error \u2192 fix \u2192 repeat"),
    ("3", "Data: signals, windows & labels", "Turning time-series into lessons"),
    ("4", "The 'wrong cue' trap (shortcut learning)", "Why a great-looking model can fail"),
    ("5", "What a neural network is", "Stacked layers that find patterns"),
    ("6", "Why convolutional / 1D networks?", "Built for patterns in signals & pictures"),
    ("7", "Measuring success: error, accuracy & friends", "Accuracy, precision, recall, F1, loss"),
    ("8", "Overfitting: memorising vs understanding", "The most important idea for beginners"),
    ("9", "Before training: split your data", "Train / validation / test"),
    ("10", "Knobs you will meet", "Learning rate, batch size, epochs, regularisation"),
    ("11", "Optimisers & class imbalance", "How weights update; uneven data"),
    ("12", "The full journey: data to device", "The whole pipeline in one picture"),
    ("Glossary", "Jargon decoded", "Plain-English definitions"),
]
rows = [["#", "Chapter", "What you will learn"]]
rows += [[r[0], P(r[1], BULLET), P(r[2], SMALL)] for r in toc]
story.append(table(rows, [14 * mm, 82 * mm, 69 * mm]))

# ---------------------------------------------------------------- 1
story.append(PageBreak())
story.append(P("1. What is machine learning?", H1))
story.append(hr())
story.append(P(
    "Normally you write the rules yourself. To detect a sick motor you might say: "
    "\u201cif it vibrates more than 0.5 g, it is broken.\u201d That is a "
    "<b>rule</b> \u2014 you, the programmer, thought of it."))
story.append(P(
    "Machine learning flips it. You show a computer many examples \u2014 readings "
    "that are healthy and readings that are broken \u2014 and the computer figures "
    "out the rules on its own. You never tell it the threshold; it discovers what "
    "matters."))
story.append(figure("01_ml_concept.png",
                    "Traditional programming (top): you give the rules. Machine "
                    "learning (bottom): you give examples, the machine finds the rules."))
story.append(P("Two words you must know", H2))
story.append(bullets([
    "<b>Training</b> \u2014 the learning phase. The computer studies examples and "
    "adjusts itself. Happens once, on a powerful PC.",
    "<b>Inference</b> \u2014 the using phase. The trained model guesses about a "
    "new, unseen example. In this project it runs on the tiny ESP32 chip.",
]))
story.append(worked("Example A \u2014 motor project", [
    "Instead of hand-writing \u201cvibration > X and current > Y = friction\u201d, "
    "we gave the computer hundreds of labelled 1-second windows. It learned the "
    "patterns itself \u2014 and got 117 of 117 right on data it had never seen.",
]))
story.append(worked("Example B \u2014 everyday", [
    "Think of spam filtering. Nobody writes \u201cif it contains the word FREE in "
    "all caps, it is spam.\u201d Instead you show it thousands of real spam and real "
    "normal emails, and it learns the patterns itself. Same idea.",
]))

# ---------------------------------------------------------------- 2
story.append(P("2. Learning by example: the training loop", H1))
story.append(hr())
story.append(P(
    "How does a computer \u201clearn\u201d? Surprisingly simply: guess, check, "
    "adjust, repeat \u2014 a lot."))
story.append(figure("02_training_loop.png",
                    "The training loop. The model gets a little better each round, "
                    "like a student who checks answers and fixes mistakes.", width_mm=115))
story.append(bullets([
    "<b>1. Predict.</b> The model looks at a window and says \u201cI think healthy.\u201d",
    "<b>2. Measure the error.</b> Compare the guess to the true label. Wrong = big error.",
    "<b>3. Nudge the weights.</b> The model\u2019s internal numbers (weights) are "
    "adjusted slightly so next time it is less wrong.",
    "<b>4. Repeat.</b> Thousands of times, until the weights settle into values "
    "that give good answers.",
]))
story.append(P(
    "Those internal numbers \u2014 the <b>weights</b> \u2014 <i>are</i> the model. "
    "Learning is just finding the right numbers. Once found, they can be saved to a "
    "file (here, under 6 KB) and shipped inside the firmware."))
story.append(worked("Example A \u2014 motor project", [
    "Round 1: model says \u201chealthy\u201d for a friction window. Wrong \u2192 "
    "big error \u2192 weights nudged toward \u201cfriction\u201d. After many rounds "
    "the error drops and the guesses become reliable.",
]))
story.append(worked("Example B \u2014 everyday", [
    "Tuning a radio by trial and error: turn the dial, listen for static, adjust, "
    "repeat until the station is clear. Training is the same \u2014 nudge, check, repeat.",
]))

# ---------------------------------------------------------------- 3
story.append(PageBreak())
story.append(P("3. Data: signals, windows & labels", H1))
story.append(hr())
story.append(P(
    "Before any model, there must be data. For our motor we measure five things "
    "many times per second: vibration on three axes (ax, ay, az), current, and "
    "rotation speed (RPM). Numbers over time form a <b>signal</b>."))
story.append(figure("03_signals.png",
                    "A healthy motor hums quietly; an imbalanced one shakes hard. "
                    "The model must tell them apart from the numbers alone."))
story.append(P("From a stream to lessons: windows & labels", H2))
story.append(P(
    "A model cannot look at an endless stream. We cut it into short, overlapping "
    "<b>windows</b> (here 50 samples \u2248 1 second, sliding by half). Each window "
    "needs a <b>label</b> \u2014 the correct answer \u2014 which we know because we "
    "created the fault on purpose."))
story.append(figure("04_windowing.png",
                    "Windowing: chop one long recording into many short 1-second "
                    "overlapping slices. Each slice becomes one training example."))
story.append(bullets([
    "<b>Signal</b> \u2014 numbers measured over time.",
    "<b>Window</b> \u2014 a short slice of the signal (~1 s here).",
    "<b>Label</b> \u2014 the known correct answer for a window.",
    "<b>Dataset</b> \u2014 all the windows plus their labels.",
    "<b>Normalisation</b> \u2014 rescaling inputs (mean 0, spread 1) so no single "
    "unit dominates (see picture below).",
]))
story.append(figure("05_normalise.png",
                    "Normalisation squashes different units (e.g. current in "
                    "milliamps) onto a common scale so the model treats them fairly."))
story.append(worked("Example A \u2014 motor project", [
    "9 recordings \u00d7 20 s at 50 Hz. Each 1 s window = one example. Label = "
    "healthy / imbalanced / friction. Windows overlap so we get more examples from "
    "the same recording.",
]))
story.append(worked("Example B \u2014 everyday", [
    "Recognising handwriting: each image is one example; the label is the letter "
    "\u201cA\u201d or \u201cB\u201d. Just like a window, each image is one labelled "
    "lesson for the model.",
]))

# ---------------------------------------------------------------- 4
story.append(P("4. The 'wrong cue' trap (shortcut learning)", H1))
story.append(hr())
story.append(P(
    "A story every beginner should hear, because it happened to us. Our first model "
    "looked excellent \u2014 92.9% correct on tests. On the real device it failed: "
    "it called everything \u201cfriction\u201d."))
story.append(P("What went wrong?", H2))
story.append(P(
    "We had accidentally included <b>supply voltage</b> as an input. By coincidence, "
    "healthy recordings were taken at ~6.02 V and fault recordings at ~6.00 V. The "
    "model noticed this tiny difference and used it as a shortcut. It never learned "
    "vibration or current \u2014 it learned \u201c6.02 V means healthy.\u201d On a "
    "different supply, that shortcut broke instantly."))
story.append(figure("09_leakage.png",
                    "Shortcut learning: the model separated healthy vs fault by a "
                    "20 mV voltage difference instead of the real physical signature."))
story.append(worked("Example A \u2014 motor project (fixed)", [
    "We removed voltage and retrained. Forced to use vibration + current (the real "
    "causes), the model became both more accurate (96.6% \u2192 100% on the new rig) "
    "and far more robust.",
]))
story.append(worked("Example B \u2014 everyday", [
    "A model that tells apart photos of huskies vs wolves \u2014 but every wolf photo "
    "happened to have snow in the background. It learned \u201csnow = wolf,\u201d not "
    "\u201cwolf\u201d. It fails on a wolf in a forest. Same trap.",
]))
story.append(callout(
    "Remember this",
    "A model learns whatever is <i>easiest</i>, not whatever is <i>true</i>. Called "
    "<b>shortcut learning</b> / <b>feature leakage</b>. Always ask: \u201cis this "
    "input a real cause, or just a coincidence in my data?\u201d"))

# ---------------------------------------------------------------- 5

# ---------------------------------------------------------------- 5
story.append(PageBreak())
story.append(P("5. What a neural network is", H1))
story.append(hr())
story.append(P(
    "A neural network is a stack of simple maths, layered like an assembly line. "
    "Each layer takes numbers in, does a little calculation, and passes the result "
    "on. The final layer produces the answer \u2014 here, three scores: healthy, "
    "imbalanced, friction."))
story.append(bullets([
    "<b>Neuron</b> \u2014 the smallest unit: multiply inputs by weights, add them up, "
    "pass through a simple function.",
    "<b>Layer</b> \u2014 a row of neurons side by side.",
    "<b>Weights</b> \u2014 the numbers tuned during training. The model\u2019s memory.",
    "<b>Activation function</b> \u2014 a small bend so the network can learn curvy "
    "patterns, not just straight lines.",
    "<b>Depth</b> \u2014 the number of layers. \u201cDeep\u201d learning = many layers.",
]))
story.append(P(
    "More layers can learn more complex patterns, but need more data and power. Our "
    "motor model is <b>small and shallow on purpose</b> so it fits a tiny chip."))
story.append(worked("Example A \u2014 motor project", [
    "Its whole network is just a handful of layers with 963 numbers in total \u2014 "
    "small enough for a microcontroller, big enough to spot the fault patterns.",
]))
story.append(worked("Example B \u2014 everyday", [
    "A network that recognises cat pictures stacks many layers: early layers see "
    "edges, middle layers see eyes and ears, deep layers see \u201cwhole cat.\u201d "
    "Same layered idea, just bigger.",
]))

# ---------------------------------------------------------------- 6
story.append(P("6. Why convolutional / 1D networks?", H1))
story.append(hr())
story.append(P(
    "A plain network treats every number separately. That is wasteful for a "
    "<b>signal</b>, where what matters is the <i>shape and rhythm</i>. A "
    "<b>convolutional neural network (CNN)</b> slides small pattern-detectors across "
    "the signal, so it recognises a shape wherever it appears."))
story.append(figure("06_cnn_layers.png",
                    "A small 1D CNN. Each layer finds a slightly more complex "
                    "pattern, then the network shrinks the data and decides the class."))
story.append(P("Why '1D'?", H2))
story.append(P(
    "Images are 2D (height \u00d7 width), so image CNNs slide in two directions. "
    "Our data is a single line over time (5 channels \u00d7 50 samples), so we slide "
    "across time in one direction: <b>1D</b>."))
story.append(bullets([
    "<b>Loves signals.</b> Faults are repeating shapes \u2014 exactly what "
    "convolutions detect.",
    "<b>Same-pattern-anywhere.</b> A vibration spike is recognised at the start or "
    "end of a window alike.",
    "<b>Small & cheap.</b> Weights are shared across time, so the model is tiny "
    "(~963 numbers) \u2014 perfect for a microcontroller.",
]))
story.append(worked("Example A \u2014 motor project", [
    "Two convolution layers find vibration and current patterns, a pooling step "
    "shrinks everything, and one layer decides. 963 weights, under 6 KB, 28 ms per "
    "decision on a \u20ac5 chip.",
]))
story.append(worked("Example B \u2014 everyday", [
    "Face detection in phone cameras uses 2D CNNs: a \u201ceye-shaped\u201d detector "
    "fires wherever eyes appear in the picture. Same sliding-detector idea, 2D.",
]))

# ---------------------------------------------------------------- 7
story.append(PageBreak())
story.append(P("7. Measuring success: error, accuracy & friends", H1))
story.append(hr())
story.append(P(
    "You can only improve what you can measure. This is the chapter beginners "
    "underrate most. \u201c95% accurate\u201d can be fantastic or terrible depending "
    "on the data \u2014 here is how to read it correctly."))
story.append(P("Error and loss", H2))
story.append(P(
    "<b>Error</b> is how wrong you are. <b>Loss</b> is the number the model minimises "
    "while training \u2014 a smooth measure of wrongness (e.g. cross-entropy, which "
    "punishes confident wrong answers hard). Accuracy is a rough summary; loss is "
    "what actually drives learning."))
story.append(P("Accuracy alone can fool you", H2))
story.append(P(
    "Imagine 95% of motors are healthy. A lazy model that always says "
    "\u201chealthy\u201d scores <b>95% accuracy</b> \u2014 and never catches a single "
    "fault! This is the <b>imbalance problem</b>. To see what is really happening, "
    "we look inside with a <b>confusion matrix</b>."))
story.append(figure("10_confusion.png",
                    "A confusion matrix. Rows = actual class, columns = predicted "
                    "class. The diagonal is correct; off-diagonal cells are mistakes. "
                    "Here we can see exactly which classes get confused."))
story.append(P("Precision and recall", H2))
story.append(figure("11_precision_recall.png",
                    "Precision asks: of the ones I flagged, how many were right? "
                    "Recall asks: of all the real cases, how many did I catch?"))
story.append(table([
    ["Metric", "Question it answers", "Formula (plain)"],
    ["Accuracy", "Overall, how often right?", "(all correct) / (all examples)"],
    ["Precision", "Of those I flagged faulty, how many were?", "correct faulty / all I flagged faulty"],
    ["Recall", "Of all the truly faulty, how many did I catch?", "correct faulty / all truly faulty"],
    ["F1 score", "A fair single number balancing both", "harmonic mean of precision & recall"],
], [24 * mm, 70 * mm, 71 * mm], font_size=8.8))
story.append(callout(
    "Which matters more?",
    "It depends. Missing a real fault (low <b>recall</b>) can be dangerous; crying "
    "wolf too often (low <b>precision</b>) is annoying. F1 blends both. For "
    "motor health, recall usually matters most \u2014 you do not want to miss a "
    "failing motor."))
story.append(worked("Example A \u2014 worked numbers (motor project style)", [
    "Suppose 100 windows: 60 healthy, 20 imbalanced, 20 friction. The model "
    "predicts 57 healthy, 23 imbalanced, 20 friction correctly, but wrongly calls "
    "3 imbalanced as \u201chealthy\u201d and 2 healthy as \u201cfriction\u201d.",
    "\u2022 Accuracy = (57+17+20)/100 = 94%.",
    "\u2022 Recall for imbalanced = 17 caught / 20 real = 85% (missed 3!).",
    "\u2022 Precision for friction = 20 correct / 22 flagged = 91%.",
    "Lesson: 94% \u201caccuracy\u201d hid 3 missed imbalance faults \u2014 seen "
    "only via the confusion matrix / recall."]))
story.append(worked("Example B \u2014 everyday", [
    "A smoke alarm: precision = when it beeps, how often is there real smoke "
    "(false alarms hurt precision)? Recall = when there is real smoke, does it "
    "always beep (a missed fire hurts recall)? You want high recall first, then "
    "high precision.",
]))
story.append(callout(
    "In the motor project",
    "On the new motor rig the model scored 117/117 (100%) on the test windows. We "
    "still treat that with care (Section 8) because the test windows came from the "
    "same recording session \u2014 see the caveat."))

# ---------------------------------------------------------------- 8
story.append(PageBreak())
story.append(P("8. Overfitting: memorising vs understanding", H1))
story.append(hr())
story.append(P(
    "The single most important beginner concept. Imagine a student who memorises "
    "last year\u2019s exam answers. They score 100% on that paper \u2014 then fail a "
    "new paper with different questions. They did not learn the subject; they "
    "memorised the answers."))
story.append(P(
    "Models do the same: too big or trained too long, and they <b>memorise</b> the "
    "training examples instead of learning general patterns. We call this "
    "<b>overfitting</b>."))
story.append(figure("07_overfitting.png",
                    "Overfitting in one picture. Training error keeps dropping, but "
                    "validation (new-data) error starts rising. The sweet spot is the "
                    "lowest point of the validation curve."))
story.append(P("How we fight it", H2))
story.append(bullets([
    "<b>Keep an exam set.</b> Hold back data the model never trains on; judge only there.",
    "<b>Early stopping.</b> Stop when the exam score stops improving.",
    "<b>Regularisation.</b> Techniques like dropout stop the model relying on one detail.",
    "<b>More, varied data.</b> The best cure \u2014 we even vary (\u00b15\u201315%) "
    "vibration to simulate real-world drift.",
]))
story.append(worked("Example A \u2014 motor project", [
    "Trained too long, the model could memorise the exact vibration of one recording "
    "and fail on a new one. Early stopping + augmentation + a held-out test file "
    "prevent this. We also warn: 100% on same-session data is encouraging but not "
    "proof of cross-day robustness.",
]))
story.append(worked("Example B \u2014 everyday", [
    "A student who memorises 100 practice questions may fail the real exam. A student "
    "who understands the method passes both. \u201cUnderstanding over memorising\u201d "
    "= \u201cgeneralising over overfitting.\u201d",
]))

# ---------------- chapters 9-12 + glossary + build ----------------

# ---------------------------------------------------------------- 9
story.append(PageBreak())
story.append(P("9. Before training: split your data", H1))
story.append(hr())
story.append(P(
    "You must never judge a model on the data it learned from \u2014 that is like "
    "giving a student the exam answers to study and then testing with the same paper. "
    "So we split the data into three parts."))
story.append(figure("12_data_split.png",
                    "Split data into training (learn), validation (tune/early-stop), "
                    "and test (final unbiased exam)."))
story.append(bullets([
    "<b>Training set</b> \u2014 the model learns from these.",
    "<b>Validation set</b> \u2014 used to tune choices and to decide when to stop.",
    "<b>Test set</b> \u2014 touched only at the end, for an honest final score.",
]))
story.append(P(
    "There is also <b>k-fold cross-validation</b>: split into k chunks and rotate "
    "which chunk is the test set, averaging the scores. Great when data is scarce, "
    "because every example gets a turn as the exam."))
story.append(callout(
    "Split by group, not by random rows (important for time-series)",
    "In the motor project, overlapping windows from the <i>same recording</i> must "
    "not be split across train and test \u2014 they would leak and inflate the score. "
    "We split by <b>whole capture file</b>: the test files are recordings the model "
    "never saw at all."))
story.append(worked("Example A \u2014 motor project", [
    "Test files (e.g. healthy_9, imbalanced_9, friction_9 from one capture) are held "
    "out entirely. Everything else trains. This is why the 117/117 result means "
    "something \u2014 the test windows are from whole unseen recordings.",
]))
story.append(worked("Example B \u2014 everyday", [
    "Studying for an exam: your homework (training) should not be the exact questions "
    "on the exam (test). If it is, your grade reflects memory, not understanding.",
]))

# ---------------------------------------------------------------- 10
story.append(P("10. Knobs you will meet", H1))
story.append(hr())
story.append(P(
    "These are the settings (\u201chyperparameters\u201d) you choose before training. "
    "You are not forced to guess blindly \u2014 the validation set tells you when a "
    "choice is good."))
story.append(P("Learning rate", H2))
story.append(P(
    "How big a step the model takes when nudging weights. Too small: learning crawls. "
    "Too big: it overshoots and bounces around. Finding a good value matters a lot."))
story.append(figure("13_learning_rate.png",
                    "Learning rate = step size. Too small is slow; too big is unstable; "
                    "a good one descends smoothly."))
story.append(P("Other important knobs", H2))
story.append(table([
    ["Knob", "What it does", "Typical effect"],
    ["Learning rate", "Step size when updating weights", "Too big = unstable; too small = slow"],
    ["Batch size", "How many examples per weight update", "Bigger = smoother but more memory"],
    ["Epochs", "How many full passes over the data", "Too many = overfitting"],
    ["Dropout", "Randomly ignores neurons while training", "Reduces overfitting"],
    ["Regularisation (weight decay)", "Gently keeps weights small", "Reduces overfitting"],
], [40 * mm, 66 * mm, 59 * mm], font_size=8.8))
story.append(worked("Example A \u2014 motor project", [
    "Settings used: learning rate 0.001, batch size 32, up to 80 epochs with early "
    "stopping (stop if validation does not improve for 15 epochs), dropout 0.5, small "
    "weight decay. These were tuned on the validation set, not the test set.",
]))
story.append(worked("Example B \u2014 everyday", [
    "Learning rate is like the size of steps when walking downhill in fog. Tiny steps "
    "\u2192 you never arrive. Huge leaps \u2192 you fall down the wrong side. Balanced "
    "steps get you to the bottom.",
]))

# ---------------------------------------------------------------- 11
story.append(PageBreak())
story.append(P("11. Optimisers & class imbalance", H1))
story.append(hr())
story.append(P("Optimisers: how weights get updated", H2))
story.append(P(
    "An <b>optimiser</b> is the rule that decides how to turn the error into weight "
    "changes. The simplest is <b>gradient descent</b>: move weights slightly in the "
    "direction that reduces error. <b>SGD</b> does it on small batches; "
    "<b>Adam</b> adapts the step per weight and is a very common, forgiving default."))
story.append(bullets([
    "<b>Gradient descent</b> \u2014 follow the slope downhill, one step at a time.",
    "<b>SGD (stochastic)</b> \u2014 do it on small random batches; faster and noisier.",
    "<b>Adam</b> \u2014 adaptive, per-weight step sizes; robust and popular (we use it).",
]))
story.append(P("Class imbalance: when one class is rare", H2))
story.append(P(
    "If faults are rare (say 1 in 100 motors), a model that always says \u201chealthy\u201d "
    "is 99% accurate but useless. Fixes: collect more of the rare class, weight it "
    "more in the loss, or resample the data. Always check per-class recall, not just "
    "accuracy (see Chapter 7)."))
story.append(worked("Example A \u2014 motor project", [
    "We captured each state in equal amounts (3 files per class) to keep classes "
    "balanced, and we judge with a confusion matrix so a good-looking accuracy can "
    "never hide a missed fault.",
]))
story.append(worked("Example B \u2014 everyday", [
    "Fraud detection: fraud is extremely rare. Accuracy would look great by never "
    "flagging anything \u2014 so banks track recall and precision on the rare class "
    "instead.",
]))

# ---------------------------------------------------------------- 12
story.append(P("12. The full journey: data to device", H1))
story.append(hr())
story.append(P(
    "Here is how all the pieces fit together in a real project \u2014 from raw "
    "numbers to a working device on your desk."))
story.append(figure("08_pipeline.png",
                    "The ML pipeline. Raw data is collected, cleaned, used to train a "
                    "model, tested, compressed, and deployed to run on the device."))
story.append(bullets([
    "<b>Collect</b> \u2014 record sensor data while creating each fault on purpose.",
    "<b>Clean & window</b> \u2014 tidy it and slice into labelled 1-second windows.",
    "<b>Train</b> \u2014 let the model learn (the training loop).",
    "<b>Evaluate</b> \u2014 check accuracy, confusion matrix, per-class recall on unseen data.",
    "<b>Compress</b> \u2014 quantise (INT8) so it fits the chip.",
    "<b>Deploy</b> \u2014 run it on the ESP32 for live, offline decisions.",
]))
story.append(P(
    "Notice: \u201ctrain the model\u201d is one step. Most of the effort is data, "
    "splitting, and testing. That is true of nearly every real ML project."))
story.append(callout(
    "Where to go next",
    "Once these ideas feel familiar, read the deeper project guide "
    "(\u201cML_Guide_for_Motor_Health.pdf\u201d). You will recognise every concept "
    "\u2014 now with real numbers attached.",
    bg=LIGHT, edge="#1f6feb"))

# ---------------------------------------------------------------- GLOSSARY
story.append(PageBreak())
story.append(P("Glossary \u2014 jargon in plain English", H1))
story.append(hr())
gloss = [
    ["Term", "Plain meaning"],
    ["Model", "The learned set of numbers (weights) turning inputs into a guess."],
    ["Training", "Learning phase: adjust weights using examples."],
    ["Inference", "Using phase: predict with a trained model."],
    ["Weights / parameters", "The internal numbers a model tunes while learning."],
    ["Feature", "One measured input (e.g. current, vibration on the x-axis)."],
    ["Label", "The correct answer for a training example (e.g. \u201cfriction\u201d)."],
    ["Signal", "Measurements over time."],
    ["Window", "A short slice of a signal used as one training example."],
    ["Normalisation", "Rescaling inputs to a common range (mean 0, spread 1)."],
    ["Dataset", "All the examples plus their labels."],
    ["Training set", "Data the model learns from."],
    ["Validation set", "Data used to tune settings and decide when to stop."],
    ["Test set", "Data used once at the end for an honest score."],
    ["Cross-validation", "Rotating which chunk is the test set, then averaging."],
    ["Epoch", "One full pass over the training set."],
    ["Batch", "A small group of examples processed before one weight update."],
    ["Loss", "A number measuring wrongness; training tries to make it small."],
    ["Error", "How wrong a prediction is."],
    ["Accuracy", "Fraction of predictions that are correct."],
    ["Precision", "Of the items flagged, the fraction that were correct."],
    ["Recall", "Of the real items, the fraction that were caught."],
    ["F1 score", "A single number balancing precision and recall."],
    ["Confusion matrix", "A table of actual vs predicted counts showing which classes get mixed up."],
    ["Class imbalance", "Some classes are far rarer than others."],
    ["Feature leakage", "An input that accidentally reveals the answer."],
    ["Shortcut learning", "Model relies on an easy-but-wrong cue, not the real cause."],
    ["Generalisation", "Doing well on new, unseen data (the real goal)."],
    ["Overfitting", "Memorising training data; doing poorly on new data."],
    ["Underfitting", "Too simple; does poorly even on training data."],
    ["Regularisation", "Techniques that discourage overfitting (e.g. weight decay)."],
    ["Dropout", "Randomly ignore neurons during training to prevent overfitting."],
    ["Learning rate", "Step size when updating weights."],
    ["Batch size", "Number of examples per weight update."],
    ["Optimiser", "The rule that turns error into weight changes (SGD, Adam)."],
    ["Convolution", "A small pattern-detector slid across a signal or image."],
    ["CNN", "Convolutional Neural Network \u2014 a network built from convolutions."],
    ["Activation function", "A small non-linear bend that lets the network learn complex patterns."],
    ["Depth", "Number of layers in a network."],
    ["Quantisation", "Storing weights in fewer bits (INT8) to shrink & speed up a model."],
    ["INT8", "8-bit integers \u2014 a compact way to store weights on tiny chips."],
    ["Edge AI", "Running ML on a small local device, not the cloud."],
    ["TFLM", "TensorFlow Lite Micro \u2014 a tiny runtime for ML on microcontrollers."],
]
story.append(table(gloss, [42 * mm, 123 * mm], font_size=8.5))
story.append(Spacer(1, 3 * mm))
story.append(hr())
story.append(P("Made for the motor-health-edge-ai project \u2014 a friendly on-ramp "
               "to deep learning.", SMALL))

# ---------------------------------------------------------------- BUILD
doc = SimpleDocTemplate(
    os.path.join(HERE, "ML_Primer_for_Beginners.pdf"), pagesize=A4,
    leftMargin=22 * mm, rightMargin=22 * mm,
    topMargin=20 * mm, bottomMargin=18 * mm,
    title="Machine Learning Explained Simply - A Beginner Primer",
    author="motor-health-edge-ai",
)


def _footer(canvas, doc_):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(22 * mm, 10 * mm, "Machine Learning, Explained Simply")
    canvas.drawRightString(A4[0] - 22 * mm, 10 * mm, "Page %d" % doc_.page)
    canvas.restoreState()


doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
print("Wrote ML_info/ML_Primer_for_Beginners.pdf")
