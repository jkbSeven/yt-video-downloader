import sys
import re
import os
import ffmpeg
from pytube import YouTube, exceptions
from PyQt6.QtWidgets import QApplication, QMainWindow, QLineEdit, QLabel,\
    QFileDialog, QHBoxLayout, QVBoxLayout, QWidget, QCheckBox, QComboBox, QGridLayout, QPushButton, QMessageBox
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from pathlib import Path


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Download from YouTube')
        self.setWindowIcon(QIcon('')) # Put the path to the icon in the single quotes
        self.setFixedSize(QSize(650, 370))

        info_widget = GetInfoWidget()

        combined = QWidget()
        combined_layout = QVBoxLayout()
        combined_layout.addWidget(info_widget)
        combined.setLayout(combined_layout)

        self.setCentralWidget(combined)
        self.show()


class GetInfoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.yt = None
        self.yt_author = None
        self.yt_title = None
        self.yt_views = None
        self.video_data = {}
        self.audio_data = {}

        link_label = QLabel("Link:")
        self.link_input = QLineEdit()
        self.link_input.textChanged.connect(self.get_initial_info)

        self.author_label = QLabel()
        self.title_label = QLabel()
        self.views_label = QLabel()
        self.update_initial_info_labels()

        self.selections = FormatSelection(self)

        link_section = QWidget()
        link_section_grid = QGridLayout()
        link_section_grid.addWidget(link_label, 0, 0)
        link_section_grid.addWidget(self.link_input, 0, 1)
        link_section.setLayout(link_section_grid)

        self.vertical = QVBoxLayout()
        self.vertical.addWidget(link_section)
        self.vertical.addWidget(self.author_label)
        self.vertical.addWidget(self.title_label)
        self.vertical.addWidget(self.views_label)
        self.vertical.addWidget(self.selections)

        self.setLayout(self.vertical)

    def update_initial_info_labels(self):
        self.author_label.setText(f"Author: {self.yt_author}")
        self.title_label.setText(f"Title: {self.yt_title}")
        self.views_label.setText(f"Views count: {self.yt_views}")


    # getting basic info about the video
    def get_initial_info(self):
        try:
            link = self.link_input.text()
            self.yt = YouTube(link)
        except exceptions.RegexMatchError:
            self.yt = None
            self.link_input.setStyleSheet("border: 1px solid red")
        else:
            self.link_input.setStyleSheet("border: 1px solid green")

            self.yt_author = self.yt.author
            self.yt_title = self.yt.title
            self.yt_views = self.yt.views

            self.update_initial_info_labels()
            self.get_video_data()
            self.get_audio_data()

            self.selections.video_handler()
            self.selections.audio_handler()

            self.selections.download_section.download_button.setStyleSheet("")

    # gathering all video qualities, codecs and their coresponding itags
    def get_video_data(self):
        video_resolutions = self.yt.streams.filter(adaptive=True, only_video=True).order_by('resolution')[::-1]
        video_resolutions_str = [str(stream) for stream in video_resolutions]
        self.video_data.clear()
        for stream in video_resolutions_str:
            regex_result = re.search(r'itag="(\d+)" .* res="(\w+)" .* vcodec="([\w\.]+)"', stream)
            if regex_result is not None:
                self.video_data[regex_result.group(1)] = {
                    'res': regex_result.group(2),
                    'vcodec': regex_result.group(3)
                }

    # gathering all audio bitrates, codecs and their coresponding itags
    def get_audio_data(self):
        audio_bitrate = self.yt.streams.filter(adaptive=True, only_audio=True).order_by('abr')[::-1]
        audio_bitrate_str = [str(stream) for stream in audio_bitrate]
        self.audio_data.clear()
        for stream in audio_bitrate_str:
            regex_result = re.search(r'itag="(\d+)".*abr="(\w+)".*acodec="([\w\.]+)"', stream)
            if regex_result is not None:
                self.audio_data[regex_result.group(1)] = {
                    'bitrate': regex_result.group(2),
                    'acodec': regex_result.group(3)
                }


class FormatSelection(QWidget):
    def __init__(self, info_widget):
        super().__init__()
        self.info_widget = info_widget
        self.download_section = DownloadSection(self.info_widget)
        self.selected_video_quality = None
        self.selected_audio_quality = None

        self.video_checkbox = QCheckBox("Video")
        self.video_checkbox.stateChanged.connect(self.video_handler)
        self.audio_checkbox = QCheckBox("Audio")
        self.audio_checkbox.stateChanged.connect(self.audio_handler)


        self.video_combobox = QComboBox()
        self.video_combobox.currentIndexChanged.connect(self.video_choice)
        self.audio_combobox = QComboBox()
        self.audio_combobox.currentIndexChanged.connect(self.audio_choice)

        self.video_checkbox.setChecked(True)
        self.audio_checkbox.setChecked(True)

        checkboxes = QWidget()
        checkboxes_layout = QHBoxLayout()
        checkboxes_layout.addWidget(self.video_checkbox)
        checkboxes_layout.addWidget(self.audio_checkbox)
        checkboxes.setLayout(checkboxes_layout)

        comboboxes = QWidget()
        comboboxes_layout = QHBoxLayout()
        comboboxes_layout.addWidget(self.video_combobox)
        comboboxes_layout.addWidget(self.audio_combobox)
        comboboxes.setLayout(comboboxes_layout)

        combined_layout = QVBoxLayout()
        combined_layout.addWidget(checkboxes)
        combined_layout.addWidget(comboboxes)
        combined_layout.addWidget(self.download_section)

        self.setLayout(combined_layout)

    def video_handler(self):
        if self.video_checkbox.isChecked():
            self.video_combobox.clear()
            self.video_combobox.setVisible(True) 
            if self.info_widget.yt is not None:
                for itag in self.info_widget.video_data.values(): # accessing video qualities and codecs that were gathered at earlier stage
                    resolution, vcodec = itag.values()
                    self.video_combobox.addItem(f"{resolution}, {vcodec}")
        else:
            self.video_combobox.setVisible(False) # if video checkbox is unchecked hide the box with quality selection and set video quality to None
            self.selected_video_quality = None
            self.download_section.update_itags(self.selected_video_quality, self.selected_audio_quality)

    # same procedure as with video
    def audio_handler(self):
        if self.audio_checkbox.isChecked():
            self.audio_combobox.clear()
            self.audio_combobox.setVisible(True)
            if self.info_widget.yt is not None:
                for itag in self.info_widget.audio_data.values():
                    bitrate, acodec = itag.values()
                    self.audio_combobox.addItem(f"{bitrate}, {acodec}")
        else:
            self.audio_combobox.setVisible(False)
            self.selected_audio_quality = None
            self.download_section.update_itags(self.selected_video_quality, self.selected_audio_quality)


    # getting index of the video quality that user chose and making sure that if no data is available error doesn't appear 
    def video_choice(self, index):
        if len(self.info_widget.video_data) >= 1:
            self.selected_video_quality = str(list(self.info_widget.video_data.keys())[index])
        else:
            self.selected_video_quality = None
        self.download_section.update_itags(self.selected_video_quality, self.selected_audio_quality) # updating selections

    # same procedure as with video
    def audio_choice(self, index):
        if len(self.info_widget.audio_data) >= 1:
            self.selected_audio_quality = str(list(self.info_widget.audio_data.keys())[index])
        else:
            self.selected_audio_quality = None
        self.download_section.update_itags(self.selected_video_quality, self.selected_audio_quality)


class DownloadSection(QWidget):
    def __init__(self, info_widget):
        super().__init__()
        self.info_widget = info_widget
        self._video_quality_itag = None
        self._audio_quality_itag = None
        self.video_stream = None
        self.audio_stream = None
        self.video_size = 0
        self.audio_size = 0

        self.size_label = QLabel()
        self.update_size_label()

        self.filepath_input = QLineEdit()
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_filesystem)

        filepath_widget = QWidget()
        filepath_layout = QGridLayout()
        filepath_layout.addWidget(QLabel("Path to file:"), 0, 0)
        filepath_layout.addWidget(self.filepath_input, 0, 1)
        filepath_layout.addWidget(browse_button, 0, 2)
        filepath_widget.setLayout(filepath_layout)

        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.download_streams)


        downloads = QVBoxLayout()
        downloads.addWidget(self.size_label)
        downloads.addWidget(filepath_widget)
        downloads.addWidget(self.download_button)
        self.setLayout(downloads)

    @property
    def video_quality_itag(self):
        return self._video_quality_itag

    @video_quality_itag.setter
    def video_quality_itag(self, quality):
        self._video_quality_itag = quality

    @property
    def audio_quality_itag(self):
        return self._audio_quality_itag

    @audio_quality_itag.setter
    def audio_quality_itag(self, quality):
        self._audio_quality_itag = quality

    def update_itags(self, video_itag, audio_itag):
        if video_itag is not None:
            self.video_quality_itag = int(video_itag)
            self.video_stream = self.info_widget.yt.streams.get_by_itag(self.video_quality_itag) # getting pytube object
            self.video_size = self.video_stream.filesize_mb
        else: # video is not selected or no data available
            self.video_quality_itag = None
            self.video_stream = None
            self.video_size = 0

        # same as with video
        if audio_itag is not None:
            self.audio_quality_itag = int(audio_itag)
            self.audio_stream = self.info_widget.yt.streams.get_by_itag(self.audio_quality_itag)
            self.audio_size = self.audio_stream.filesize_mb
        else:
            self.audio_quality_itag = None
            self.audio_stream = None
            self.audio_size = 0

        self.update_size_label()

    def update_size_label(self):
        self.size_label.setText(f"Estimated size: {(self.video_size + self.audio_size): .2f} MB")

    # selecting path where file(s) will be saved
    def browse_filesystem(self):
        directory = str(QFileDialog.getExistingDirectory(self, "Select directory"))

        if directory:
            path = Path(directory)
            self.filepath_input.setText(str(path))

    # download using pytube
    def download_streams(self):
        if self.video_stream is not None or self.audio_stream is not None:
            path = self.filepath_input.text()
            author = self.info_widget.yt.author
            if os.path.isdir(path):
                try:
                    if self.video_stream is not None:
                        self.video_stream.download(output_path=path,
                                                   filename=f"{author}_video_{self.video_stream.default_filename}")
                    if self.audio_stream is not None:
                        self.audio_stream.download(output_path=path,
                                                   filename=f"{author}_audio_{self.audio_stream.default_filename}")
                except Exception: # really poor error handling, to be improved
                    QMessageBox.critical(self, "Download error", "pytube related download error",
                                         buttons=QMessageBox.StandardButton.Ok)
                else:
                    if self.video_stream is not None and self.audio_stream is not None:
                        video_path = os.path.abspath(f"{path}\\{author}_video_{self.video_stream.default_filename}")
                        audio_path = os.path.abspath(f"{path}\\{author}_audio_{self.audio_stream.default_filename}")
                        input_video = ffmpeg.input(video_path)
                        input_audio = ffmpeg.input(audio_path)

                        # video and audio merge
                        ffmpeg.concat(input_video, input_audio, v=1, a=1).output(
                            f'{path}\\{author}_combined_{self.video_stream.default_filename.split(".")[0]}.mp4').run()
                        os.remove(video_path)
                        os.remove(audio_path)
                    self.download_button.setStyleSheet("border: 1px solid green")
            else:
                QMessageBox.critical(self, "Download error", "Invalid download path",
                                     buttons=QMessageBox.StandardButton.Ok)
                self.download_button.setStyleSheet("border: 1px solid red")
        else:
            QMessageBox.critical(self, "Download error", "You need to select at least one media type to download",
                                 buttons=QMessageBox.StandardButton.Ok)
            self.download_button.setStyleSheet("border: 1px solid red")


app = QApplication(sys.argv)
window = MainWindow()
sys.exit(app.exec())
