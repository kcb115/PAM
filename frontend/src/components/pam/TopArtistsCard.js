import React, { useState } from "react";

export default function TopArtistsCard({ artists = [] }) {
  const [showAll, setShowAll] = useState(false);

  if (!artists || artists.length === 0) return null;

  const topTen = artists.slice(0, 10);
  const remaining = artists.slice(10);

  return (
    <div className="bg-white shadow-md rounded-2xl p-6 mt-6">
      <h2 className="text-xl font-semibold mb-4">Top Spotify Artists</h2>

      <ul className="space-y-2">
        {topTen.map((artist, index) => (
          <li
            key={index}
            className="flex justify-between border-b pb-1 text-gray-700"
          >
            <span>{index + 1}. {artist}</span>
          </li>
        ))}
      </ul>

      {remaining.length > 0 && (
        <div className="mt-4">
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-blue-600 hover:underline text-sm"
          >
            {showAll ? "Show Less" : `See All (${artists.length})`}
          </button>

          {showAll && (
            <ul className="mt-3 space-y-2 max-h-64 overflow-y-auto">
              {remaining.map((artist, index) => (
                <li
                  key={index + 10}
                  className="flex justify-between border-b pb-1 text-gray-700"
                >
                  <span>{index + 11}. {artist}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
