import whisper
import os
import subprocess
import re
from whisper.utils import WriteSRT


def transcribe_audio_to_srt(video_path, output_dir):
    """
    转录音频文件并保存为 SRT 字幕文件

    :param video_path: 视频文件路径
    :param output_dir: 输出目录
    :return: 生成的 SRT 文件路径
    """
    # 清理文件名：移除特殊字符，用下划线替代空格
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    video_name = re.sub(r'[^\w\s-]', '', video_name)  # 移除非字母数字、下划线、短横线、空格的字符
    video_name = re.sub(r'[\s_-]+', '_', video_name)  # 将连续空格/短横线替换为单个下划线

    # 生成音频路径和SRT路径
    audio_path = os.path.join(output_dir, f"{video_name}.wav")  # 音频文件存到输出目录
    output_srt_path = os.path.join(output_dir, f"{video_name}.srt")

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 用ffmpeg提取音频
    if not os.path.exists(audio_path):
        print(f"开始提取音频：{video_path} -> {audio_path}")
        ffmpeg_command = [
            "ffmpeg",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            audio_path
        ]
        try:
            subprocess.run(ffmpeg_command, check=True)
            print(f"音频提取完成：{audio_path}")
        except subprocess.CalledProcessError as e:
            print(f"音频提取失败：{e}")
            return None

    # 加载模型
    model = whisper.load_model("medium", device="cpu")

    # 语音识别
    result = model.transcribe(audio_path)

    # 生成SRT文件
    writer = WriteSRT(output_dir)  # 修正：传入输出目录而不是完整路径
    writer(result, audio_path)  # 自动生成文件名

    print(f"SRT 文件已生成: {output_srt_path}")
    return output_srt_path


if __name__ == "__main__":
    video_path = r"E:\ai\[ANi] Lycoris Recoil 莉可麗絲：友誼是時間的竊賊 - 01 [1080P][Baha][WEB-DL][AAC AVC][CHT].mp4"
    output_dir = r"E:\ai"
    srt_file_path = transcribe_audio_to_srt(video_path, output_dir)