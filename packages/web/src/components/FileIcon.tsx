import {
  File,
  FileArchive,
  FileAudio,
  FileCode,
  FileImage,
  FileText,
  FileVideo,
  Lock,
} from 'lucide-react';
import { fileIconKind } from '../lib/format';
import { classNames } from '../lib/format';

const TONES: Record<string, string> = {
  image: 'bg-fuchsia-500/10 text-fuchsia-300',
  video: 'bg-purple-500/10 text-purple-300',
  audio: 'bg-orange-500/10 text-orange-300',
  pdf: 'bg-rose-500/10 text-rose-300',
  archive: 'bg-amber-500/10 text-amber-300',
  code: 'bg-cyan-500/10 text-cyan-300',
  text: 'bg-emerald-500/10 text-emerald-300',
  file: 'bg-slate-500/10 text-slate-300',
};

export default function FileIcon({
  name,
  type,
  size = 'md',
}: {
  name: string;
  type: string;
  size?: 'sm' | 'md' | 'lg';
}): JSX.Element {
  const kind = fileIconKind(name, type);
  const Icon =
    kind === 'image'
      ? FileImage
      : kind === 'video'
        ? FileVideo
        : kind === 'audio'
          ? FileAudio
          : kind === 'pdf'
            ? FileText
            : kind === 'archive'
              ? FileArchive
              : kind === 'code'
                ? FileCode
                : kind === 'text'
                  ? FileText
                  : File;
  const dimensions = size === 'lg' ? 'h-12 w-12' : size === 'sm' ? 'h-8 w-8' : 'h-10 w-10';
  const iconSize = size === 'lg' ? 'h-6 w-6' : size === 'sm' ? 'h-4 w-4' : 'h-5 w-5';
  return (
    <span
      className={classNames(
        'relative flex shrink-0 items-center justify-center rounded-xl',
        TONES[kind],
        dimensions,
      )}
    >
      <Icon className={iconSize} />
      <span className="absolute -bottom-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full border border-[#0b111d] bg-emerald-500 text-slate-950">
        <Lock className="h-2.5 w-2.5" />
      </span>
    </span>
  );
}
