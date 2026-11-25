export type BrandMentionAnalysis = {
  mentioned: boolean;
  occurrenceCount: number;
  firstPosition: number | null;
};

function normalize(value: string): string {
  return value.trim().toLocaleLowerCase();
}

export function analyzeBrandMention(
  brandName: string,
  answer: string,
): BrandMentionAnalysis {
  const target = normalize(brandName);
  const source = normalize(answer);

  if (!target) {
    return { mentioned: false, occurrenceCount: 0, firstPosition: null };
  }

  let occurrenceCount = 0;
  let searchFrom = 0;
  let firstPosition: number | null = null;

  while (true) {
    const position = source.indexOf(target, searchFrom);

    if (position === -1) {
      break;
    }

    occurrenceCount += 1;
    firstPosition ??= position;
    searchFrom = position + target.length;
  }

  return {
    mentioned: occurrenceCount > 0,
    occurrenceCount,
    firstPosition,
  };
}
