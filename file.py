import streamlit as st
import pymupdf
import io
import ollama
import pytesseract
from PIL import Image


# ==========================================================
# TESSERACT
# ==========================================================

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# ==========================================================
# OLLAMA SUMMARY
# ==========================================================

def summarize_text(text):
    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "user",
                "content": "Summarize this text briefly:\n\n" + text
            }
        ]
    )

    return response["message"]["content"]


# ==========================================================
# OCR
# ==========================================================

def extract_text_with_ocr(doc):
    text = ""

    for page in doc:
        pix = page.get_pixmap(
            matrix=pymupdf.Matrix(2, 2)
        )

        image = Image.open(
            io.BytesIO(
                pix.tobytes("png")
            )
        )

        text += pytesseract.image_to_string(image)

    return text


# ==========================================================
# PAGE CONFIG
# ==========================================================

st.set_page_config(
    page_title="PDFForge",
    page_icon="📄",
    layout="wide"
)


# ==========================================================
# CSS
# ==========================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1500px;
        padding-top: 1rem;
        padding-bottom: 2rem;
    }

    div[data-testid="stImage"] {
        display: flex;
        justify-content: center;
    }

    div[data-testid="column"] button {
        text-align: left;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ==========================================================
# SESSION STATE
# ==========================================================

if "pdf" not in st.session_state:
    st.session_state.pdf = None

if "filename" not in st.session_state:
    st.session_state.filename = "document.pdf"

if "page" not in st.session_state:
    st.session_state.page = 0

if "zoom" not in st.session_state:
    st.session_state.zoom = 1.0

if "history" not in st.session_state:
    st.session_state.history = []

if "redo" not in st.session_state:
    st.session_state.redo = []

if "tool" not in st.session_state:
    st.session_state.tool = "Select"

if "selected_line" not in st.session_state:
    st.session_state.selected_line = None


# ==========================================================
# PDF FUNCTIONS
# ==========================================================

def get_pdf_data():
    return st.session_state.pdf.tobytes()


def save_state():

    if st.session_state.pdf:

        data = st.session_state.pdf.tobytes()

        st.session_state.history.append(data)

        st.session_state.redo.clear()


def restore_pdf(data):

    st.session_state.pdf = pymupdf.open(
        stream=data,
        filetype="pdf"
    )


def undo():

    if len(st.session_state.history) > 1:

        current = st.session_state.history.pop()

        st.session_state.redo.append(current)

        restore_pdf(
            st.session_state.history[-1]
        )


def redo():

    if st.session_state.redo:

        data = st.session_state.redo.pop()

        st.session_state.history.append(data)

        restore_pdf(data)


# ==========================================================
# RENDER PAGE
# ==========================================================

def render_page(doc, page_number, zoom):

    page = doc[page_number]

    matrix = pymupdf.Matrix(
        zoom,
        zoom
    )

    pix = page.get_pixmap(
        matrix=matrix,
        alpha=False
    )

    return Image.open(
        io.BytesIO(
            pix.tobytes("png")
        )
    )


# ==========================================================
# GET PDF LINES
# ==========================================================

def get_pdf_lines(page):

    lines = []

    try:

        data = page.get_text("dict")

        for block in data.get("blocks", []):

            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):

                spans = line.get("spans", [])

                if not spans:
                    continue

                text = "".join(
                    span.get("text", "")
                    for span in spans
                ).strip()

                if not text:
                    continue

                rect = pymupdf.Rect(
                    line["bbox"]
                )

                rect.x0 -= 1
                rect.y0 -= 1
                rect.x1 += 1
                rect.y1 += 1

                font_size = spans[0].get(
                    "size",
                    11
                )

                font_name = spans[0].get(
                    "font",
                    "helv"
                )

                lines.append(
                    {
                        "text": text,
                        "rect": rect,
                        "font_size": font_size,
                        "font_name": font_name
                    }
                )

    except Exception:
        return []

    return lines


# ==========================================================
# SELECT LINE
# ==========================================================

def select_line(
    page_number,
    line_number,
    text,
    rect,
    font_size,
    font_name
):

    st.session_state.selected_line = {

        "page": page_number,

        "line": line_number,

        "text": text,

        "rect": pymupdf.Rect(rect),

        "font_size": font_size,

        "font_name": font_name
    }


# ==========================================================
# TITLE
# ==========================================================

st.title("📄 PDFForge")

st.caption(
    "Simple PDF Editor & Analyzer"
)


# ==========================================================
# UPLOAD
# ==========================================================

uploaded = st.file_uploader(
    "Upload your PDF",
    type=["pdf"],
    key="main_pdf_upload"
)


if uploaded:

    try:

        data = uploaded.read()

        new_file = (
            st.session_state.filename
            != uploaded.name
        )

        if (
            st.session_state.pdf is None
            or new_file
        ):

            doc = pymupdf.open(
                stream=data,
                filetype="pdf"
            )

            if doc.needs_pass:

                st.error(
                    "This PDF is password protected."
                )

                st.stop()

            if len(doc) == 0:

                st.error(
                    "This PDF has no pages."
                )

                st.stop()

            st.session_state.pdf = doc

            st.session_state.filename = uploaded.name

            st.session_state.page = 0

            st.session_state.selected_line = None

            st.session_state.history = [data]

            st.session_state.redo = []

    except Exception as e:

        st.error(
            f"Could not open PDF: {e}"
        )

        st.stop()


# ==========================================================
# NO PDF
# ==========================================================

if not st.session_state.pdf:

    st.info(
        "Upload a PDF above to start editing."
    )

    st.markdown(
        """
        ### PDFForge

        Edit and manage your PDF from one workspace.

        **Features**

        - Select complete PDF lines
        - Edit any text inside selected line
        - Add text
        - Add images
        - Delete selected line
        - Highlight text
        - Search PDF
        - Rotate pages
        - Add pages
        - Delete pages
        - Undo / Redo
        - Download edited PDF
        """
    )

    st.stop()


# ==========================================================
# CURRENT DOCUMENT
# ==========================================================

doc = st.session_state.pdf

page = doc[
    st.session_state.page
]


# ==========================================================
# TOOLBAR
# ==========================================================

st.divider()

st.subheader(
    "🛠 PDF Tools"
)


toolbar = st.columns(
    [
        0.5,
        0.5,
        0.9,
        0.9,
        0.9,
        0.9,
        1.0,
        0.9,
        0.9,
        0.9
    ]
)


with toolbar[0]:

    if st.button(
        "↩",
        help="Undo",
        key="toolbar_undo"
    ):

        undo()
        st.rerun()


with toolbar[1]:

    if st.button(
        "↪",
        help="Redo",
        key="toolbar_redo"
    ):

        redo()
        st.rerun()


with toolbar[2]:

    if st.button(
        "Select",
        key="tool_select"
    ):

        st.session_state.tool = "Select"
        st.rerun()


with toolbar[3]:

    if st.button(
        "✏️ Edit",
        key="tool_edit"
    ):

        st.session_state.tool = "Edit"
        st.rerun()


with toolbar[4]:

    if st.button(
        "T Text",
        key="tool_text"
    ):

        st.session_state.tool = "Text"
        st.rerun()


with toolbar[5]:

    if st.button(
        "🖼 Image",
        key="tool_image"
    ):

        st.session_state.tool = "Image"
        st.rerun()


with toolbar[6]:

    if st.button(
        "🖍 Highlight",
        key="tool_highlight"
    ):

        st.session_state.tool = "Highlight"
        st.rerun()


with toolbar[7]:

    if st.button(
        "🔍 Search",
        key="tool_search"
    ):

        st.session_state.tool = "Search"
        st.rerun()


with toolbar[8]:

    if st.button(
        "↻ Rotate",
        key="tool_rotate"
    ):

        save_state()

        page.set_rotation(
            (page.rotation + 90) % 360
        )

        st.success(
            "Page rotated."
        )

        st.rerun()


with toolbar[9]:

    if st.button(
        "🗑 Delete",
        key="tool_delete"
    ):

        st.session_state.tool = "Delete"
        st.rerun()


# ==========================================================
# SECOND TOOLBAR
# ==========================================================

toolbar2 = st.columns(
    [1, 1, 1, 1, 1, 1]
)


with toolbar2[0]:

    if st.button(
        "➕ Add Page",
        key="add_page"
    ):

        save_state()

        doc.new_page(
            width=595,
            height=842
        )

        st.session_state.page = len(doc) - 1

        st.session_state.selected_line = None

        st.success(
            "Blank page added."
        )

        st.rerun()


with toolbar2[1]:

    if st.button(
        "🗑 Delete Page",
        key="delete_page"
    ):

        if len(doc) > 1:

            save_state()

            doc.delete_page(
                st.session_state.page
            )

            st.session_state.page = max(
                0,
                st.session_state.page - 1
            )

            st.session_state.selected_line = None

            st.success(
                "Page deleted."
            )

            st.rerun()

        else:

            st.warning(
                "A PDF must have at least one page."
            )


with toolbar2[2]:

    if st.button(
        "− Zoom",
        key="zoom_out"
    ):

        st.session_state.zoom = max(
            0.6,
            st.session_state.zoom - 0.1
        )

        st.rerun()


with toolbar2[3]:

    if st.button(
        "+ Zoom",
        key="zoom_in"
    ):

        st.session_state.zoom = min(
            1.5,
            st.session_state.zoom + 0.1
        )

        st.rerun()


with toolbar2[4]:

    selected_page = st.number_input(
        "Page",
        min_value=1,
        max_value=len(doc),
        value=st.session_state.page + 1,
        key="top_page_number"
    )

    if (
        selected_page - 1
        != st.session_state.page
    ):

        st.session_state.page = (
            selected_page - 1
        )

        st.session_state.selected_line = None

        st.rerun()


with toolbar2[5]:

    st.download_button(
        "⬇ Save PDF",
        get_pdf_data(),
        "edited_" + st.session_state.filename,
        "application/pdf",
        key="toolbar_download"
    )


# ==========================================================
# CURRENT TOOL
# MOVED HERE SO IT APPEARS ABOVE THE PDF WORKSPACE
# ==========================================================

tool = st.session_state.tool


# ==========================================================
# SELECT
# ==========================================================

if tool == "Select":

    st.info(
        "Select a complete line from the left side."
    )


# ==========================================================
# EDIT
# ==========================================================

elif tool == "Edit":

    st.subheader(
        "✏️ Edit Selected Line"
    )

    selected = (
        st.session_state.selected_line
    )

    if selected is None:

        st.info(
            "Select a complete PDF line "
            "from the left side first."
        )

    elif (
        selected["page"]
        != st.session_state.page
    ):

        st.info(
            "Select a line from the current page."
        )

    else:

        st.write(
            "You can change any part "
            "of the selected line below."
        )

        st.caption(
            f"Original line: {selected['text']}"
        )

        new_text = st.text_area(
            "Edit line text",
            value=selected["text"],
            height=100,
            key=(
                f"edit_selected_line_"
                f"{selected['page']}_"
                f"{selected['line']}"
            )
        )

        if st.button(
            "Apply Text Change",
            key="apply_selected_edit"
        ):

            if not new_text.strip():

                st.warning(
                    "The line cannot be empty. "
                    "Use Delete if you want to "
                    "remove the entire line."
                )

            else:

                save_state()

                rect = pymupdf.Rect(
                    selected["rect"]
                )

                page.add_redact_annot(
                    rect,
                    fill=(1, 1, 1)
                )

                page.apply_redactions()

                font_size = max(
                    6,
                    selected.get(
                        "font_size",
                        rect.height * 0.80
                    )
                )

                insert_y = (
                    rect.y1
                    - max(
                        1,
                        font_size * 0.15
                    )
                )

                page.insert_text(
                    (
                        rect.x0 + 1,
                        insert_y
                    ),
                    new_text,
                    fontsize=font_size,
                    fontname="helv",
                    color=(0, 0, 0)
                )

                st.session_state.selected_line = None

                st.success(
                    "Selected line updated successfully."
                )

                st.rerun()


# ==========================================================
# TEXT
# ==========================================================

elif tool == "Text":

    st.subheader(
        "T Add Text"
    )

    text = st.text_input(
        "Text",
        key="new_text"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        x = st.number_input(
            "X Position",
            0.0,
            2000.0,
            50.0,
            key="text_x"
        )

    with col2:

        y = st.number_input(
            "Y Position",
            0.0,
            3000.0,
            100.0,
            key="text_y"
        )

    with col3:

        size = st.number_input(
            "Font Size",
            6.0,
            100.0,
            14.0,
            key="text_size"
        )

    color = st.color_picker(
        "Text Color",
        "#000000",
        key="text_color"
    )

    bold = st.checkbox(
        "Bold",
        key="text_bold"
    )

    if st.button(
        "Add Text to PDF",
        key="apply_text"
    ):

        if not text:

            st.warning(
                "Enter some text."
            )

        else:

            save_state()

            rgb = tuple(
                int(
                    color[i:i+2],
                    16
                ) / 255
                for i in (1, 3, 5)
            )

            font = (
                "hebo"
                if bold
                else "helv"
            )

            page.insert_text(
                (x, y),
                text,
                fontsize=size,
                fontname=font,
                color=rgb
            )

            st.success(
                "Text added."
            )

            st.rerun()


# ==========================================================
# IMAGE
# ==========================================================

elif tool == "Image":

    st.subheader(
        "🖼 Add Image"
    )

    image_file = st.file_uploader(
        "Choose an image",
        type=[
            "png",
            "jpg",
            "jpeg"
        ],
        key="image_upload"
    )

    if image_file:

        col1, col2 = st.columns(2)

        with col1:

            x = st.number_input(
                "X Position",
                0.0,
                2000.0,
                50.0,
                key="image_x"
            )

            width = st.number_input(
                "Width",
                20.0,
                1000.0,
                150.0,
                key="image_width"
            )

        with col2:

            y = st.number_input(
                "Y Position",
                0.0,
                3000.0,
                50.0,
                key="image_y"
            )

            height = st.number_input(
                "Height",
                20.0,
                1000.0,
                100.0,
                key="image_height"
            )

        if st.button(
            "Add Image to PDF",
            key="apply_image"
        ):

            save_state()

            rect = pymupdf.Rect(
                x,
                y,
                x + width,
                y + height
            )

            page.insert_image(
                rect,
                stream=image_file.read()
            )

            st.success(
                "Image added."
            )

            st.rerun()


# ==========================================================
# HIGHLIGHT
# ==========================================================

elif tool == "Highlight":

    st.subheader(
        "🖍 Highlight Text"
    )

    text = st.text_input(
        "Text to highlight",
        key="highlight_text"
    )

    if st.button(
        "Highlight",
        key="apply_highlight"
    ):

        if not text:

            st.warning(
                "Enter text to highlight."
            )

        else:

            found = page.search_for(
                text
            )

            if not found:

                st.warning(
                    "Text was not found."
                )

            else:

                save_state()

                for rect in found:

                    annotation = (
                        page.add_highlight_annot(
                            rect
                        )
                    )

                    annotation.update()

                st.success(
                    "Text highlighted."
                )

                st.rerun()


# ==========================================================
# SEARCH
# ==========================================================

elif tool == "Search":

    st.subheader(
        "🔍 Search PDF"
    )

    search_text = st.text_input(
        "Search for",
        key="search_text"
    )

    if st.button(
        "Search",
        key="search_button"
    ):

        if not search_text:

            st.warning(
                "Enter something to search."
            )

        else:

            total = 0

            for i, current_page in enumerate(doc):

                results = (
                    current_page.search_for(
                        search_text
                    )
                )

                if results:

                    total += len(results)

                    st.write(
                        f"Page {i + 1}: "
                        f"{len(results)} match(es)"
                    )

            if total == 0:

                st.warning(
                    "No matches found."
                )

            else:

                st.success(
                    f"{total} match(es) found."
                )


# ==========================================================
# DELETE
# ==========================================================

elif tool == "Delete":

    st.subheader(
        "🗑 Delete Selected Line"
    )

    selected = (
        st.session_state.selected_line
    )

    if selected is None:

        st.info(
            "Select a complete PDF line "
            "from the left side first."
        )

    elif (
        selected["page"]
        != st.session_state.page
    ):

        st.info(
            "Select a line from the current page."
        )

    else:

        st.write(
            f"**Selected:** "
            f"{selected['text']}"
        )

        if st.button(
            "Delete Selected Line",
            key="apply_selected_delete"
        ):

            save_state()

            rect = pymupdf.Rect(
                selected["rect"]
            )

            page.add_redact_annot(
                rect,
                fill=(1, 1, 1)
            )

            page.apply_redactions()

            st.session_state.selected_line = None

            st.success(
                "Selected line deleted."
            )

            st.rerun()


# ==========================================================
# WORKSPACE
# ==========================================================

st.divider()

workspace_left, workspace_right = st.columns(
    [1, 2.2],
    gap="large"
)


# ==========================================================
# LEFT SIDE — ONLY THIS AREA SCROLLS
# ==========================================================

with workspace_left:

    st.subheader(
        "📝 PDF Lines"
    )

    st.caption(
        "Click a complete line to select it."
    )

    lines = get_pdf_lines(page)

    if not lines:

        st.info(
            "No selectable text lines were found on this page."
        )

    else:

        selected = (
            st.session_state.selected_line
        )

        with st.container(
            height=600,
            border=False
        ):

            for i, item in enumerate(lines):

                is_selected = (
                    selected is not None
                    and selected["page"]
                    == st.session_state.page
                    and selected["line"]
                    == i
                )

                label = item["text"]

                if not label:
                    label = "(empty line)"

                if len(label) > 160:
                    label = label[:157] + "..."

                if is_selected:
                    label = "✅ " + label

                if st.button(
                    label,
                    key=(
                        f"pdf_line_box_"
                        f"{st.session_state.page}_"
                        f"{i}"
                    ),
                    use_container_width=True
                ):

                    select_line(
                        st.session_state.page,
                        i,
                        item["text"],
                        item["rect"],
                        item["font_size"],
                        item["font_name"]
                    )

                    st.rerun()


# ==========================================================
# RIGHT SIDE — NORMAL PDF PREVIEW
# ==========================================================

with workspace_right:

    st.subheader(
        f"📄 {st.session_state.filename}"
    )

    st.caption(
        f"Page "
        f"{st.session_state.page + 1} "
        f"of {len(doc)}"
    )

    try:

        image = render_page(
            doc,
            st.session_state.page,
            st.session_state.zoom
        )

        max_width = 850

        if image.width > max_width:

            ratio = max_width / image.width

            new_size = (
                int(image.width * ratio),
                int(image.height * ratio)
            )

            image = image.resize(
                new_size
            )

        st.image(
            image,
            width="stretch"
        )

    except Exception as e:

        st.error(
            f"Could not display page: {e}"
        )


# ==========================================================
# SELECTED LINE
# ==========================================================

selected_line = (
    st.session_state.selected_line
)


if selected_line is not None:

    st.divider()

    st.success(
        f"Selected line "
        f"{selected_line['line'] + 1}: "
        f"{selected_line['text']}"
    )

    if st.button(
        "Clear Selected Line",
        key="clear_selected_line"
    ):

        st.session_state.selected_line = None

        st.rerun()


# ==========================================================
# INFORMATION
# ==========================================================

st.divider()

info1, info2, info3 = st.columns(3)


with info1:

    st.metric(
        "Pages",
        len(doc)
    )


with info2:

    st.metric(
        "Current Page",
        st.session_state.page + 1
    )


with info3:

    size = (
        len(doc.tobytes())
        / (1024 * 1024)
    )

    st.metric(
        "PDF Size",
        f"{size:.2f} MB"
    )


# ==========================================================
# OCR + AI SUMMARY
# ==========================================================

st.divider()

st.subheader(
    "🔎 OCR & AI Summary"
)


if st.button(
    "Extract Text & Summarize",
    key="ocr_ai_button"
):

    with st.spinner(
        "Processing PDF..."
    ):

        ocr_text = extract_text_with_ocr(
            doc
        )

    if ocr_text.strip():

        st.text_area(
            "Extracted Text",
            ocr_text,
            height=250
        )

        with st.spinner(
            "Generating summary..."
        ):

            summary = summarize_text(
                ocr_text
            )

        st.subheader(
            "🤖 AI Summary"
        )

        st.write(
            summary
        )

    else:

        st.warning(
            "No text could be extracted."
        )


# ==========================================================
# FOOTER
# ==========================================================

st.divider()

st.caption(
    "PDFForge • PDF Editor & Analyzer"
)