ALTER TABLE categories ADD COLUMN color TEXT NOT NULL DEFAULT '#4E79A7';

WITH palette(position, color) AS (
    VALUES
        (0, '#4E79A7'),
        (1, '#F28E2B'),
        (2, '#B07AA1'),
        (3, '#76B7B2'),
        (4, '#EDC948'),
        (5, '#9C755F'),
        (6, '#FF9DA7'),
        (7, '#264653'),
        (8, '#7B2CBF'),
        (9, '#0077B6'),
        (10, '#BC6C25'),
        (11, '#D4A373'),
        (12, '#5A189A'),
        (13, '#0096C7'),
        (14, '#A44A3F'),
        (15, '#6D597A'),
        (16, '#E9C46A'),
        (17, '#457B9D'),
        (18, '#C77DFF'),
        (19, '#3D5A80'),
        (20, '#EE6C4D'),
        (21, '#8D6A9F'),
        (22, '#00B4D8'),
        (23, '#A98467'),
        (24, '#8338EC'),
        (25, '#FFBE0B'),
        (26, '#6096BA'),
        (27, '#B56576'),
        (28, '#6F4518'),
        (29, '#48CAE4'),
        (30, '#DDA15E'),
        (31, '#7209B7')
), ranked AS (
    SELECT id, (ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY id) - 1) % 32 AS position
    FROM categories
)
UPDATE categories SET color = (
    SELECT palette.color FROM ranked JOIN palette USING (position)
    WHERE ranked.id = categories.id
);
