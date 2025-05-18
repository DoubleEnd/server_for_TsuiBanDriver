import whisper
import os
import subprocess
from whisper.utils import WriteSRT
import torch    #验证是否有可用的gpu
from utils.fun_config import load_json

# 加载AI配置项
def get_ai_config():
    # print("加载AI配置项")
    try:
        return load_json('assets/ai_config.json')
    except FileNotFoundError:
        return {
            "valid_models": ["tiny", "small", "medium"],
            "valid_devices": ["cpu", "gpu"]
        }

# 生成字幕
def transcribe_audio_to_srt(video_path, model_type="medium", device="cpu"):
    # print("开始运行" , video_path ,"路径")
    last_slash_index = video_path.rfind("\\")
    # print(last_slash_index,"last_slash_index")
    # 使用切片获取最后一个斜杠之前的部分
    output_dir = video_path[:last_slash_index + 1]
    # print(output_dir,"output_dir")
    ai_config = get_ai_config()
    valid_models = ai_config.get("default_model", [])
    valid_devices = ai_config.get("default_device", [])

    # 参数验证
    if model_type not in valid_models:
        raise ValueError(f"无效的模型类型，可选值：{', '.join(valid_models)}")

    # 设备处理逻辑
    if device not in valid_devices:
        raise ValueError(f"无效的设备类型，可选值：{', '.join(valid_devices)}")
    if device.lower() == "gpu":
        device = "cuda"
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("请求使用GPU但CUDA不可用")

    # 获取视频文件名
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    # 生成音频路径和SRT路径
    audio_path = os.path.join(output_dir, f"{video_name}.wav")
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

    try:
        model = whisper.load_model(model_type, device=device)
        result = model.transcribe(audio_path)
        writer = WriteSRT(output_dir)
        writer(result, audio_path)

        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"已清理临时音频文件：{audio_path}")
            else:
                print(f"无需清理，音频文件不存在：{audio_path}")
        except Exception as clean_error:
            print(f"音频文件清理失败：{str(clean_error)}")
        return output_srt_path

    except Exception as e:
        raise RuntimeError(str(e))