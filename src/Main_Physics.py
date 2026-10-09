import pygame, pathlib, sys, random
try:
    from book_physics import Book, PhantomBook, BookData
except ModuleNotFoundError:
    try:
        from Book_Physics import Book, PhantomBook, BookData
    except ModuleNotFoundError:
        try:
            from BookPhysics import Book, PhantomBook, BookData
        except ModuleNotFoundError:
            from book import Book, PhantomBook, BookData
from shelf import ShelfSystem
from db import get_session, BookModel

pygame.init()
W, H = 1280, 720
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("ShelfCraft PHYSICS - flip animation")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Consolas", 16)

ROOT = pathlib.Path(__file__).parent.parent
shelf_system = ShelfSystem(ROOT / "src" / "shelves.json")
db_path = ROOT / "data" / "shelfcraft.db"
db_path.parent.mkdir(exist_ok=True)

placed_books: list[Book] = []
current_data = BookData(title="New Book", width=28, height=110, color=(random.randint(180, 230), random.randint(160, 210), random.randint(120, 180)))
drag_book = Book(current_data)
phantom = PhantomBook(current_data)
horizontal_mode = False

GRAVITY = 2200

def get_shelf_for_x(x):
    for idx, pr in enumerate(shelf_system.police_rects):
        if pr.x <= x <= pr.right:
            return idx, pr
    return -1, None

def has_support_vertical(rect, shelf_idx, exclude=None):
    if shelf_idx is None or shelf_idx < 0:
        return False
    pr = shelf_system.police_rects[shelf_idx]
    if abs(rect.bottom - pr.bottom) <= 4:
        return True
    for b in placed_books:
        if b == exclude or getattr(b, 'is_falling', False) or getattr(b, 'is_rotating', False):
            continue
        if getattr(b, 'shelf_id', -1) != shelf_idx:
            continue
        if not b.data.horizontal:
            continue
        br = b.get_rect()
        if abs(br.y - rect.bottom) <= 8:
            overlap = max(0, min(rect.right, br.right) - max(rect.x, br.x))
            if overlap >= 10:
                return True
    return False

def has_support_horizontal(rect, shelf_idx, exclude=None):
    if shelf_idx is None or shelf_idx < 0:
        return False
    pr = shelf_system.police_rects[shelf_idx]
    if abs(rect.bottom - pr.bottom) <= 4:
        return True
    vertical_supporters = []
    horizontal_supporters = []
    for b in placed_books:
        if b == exclude or getattr(b, 'is_falling', False) or getattr(b, 'is_rotating', False):
            continue
        if getattr(b, 'shelf_id', -1) != shelf_idx:
            continue
        br = b.get_rect()
        if abs(br.y - rect.bottom) <= 8:
            overlap = max(0, min(rect.right, br.right) - max(rect.x, br.x))
            if overlap <= 0:
                continue
            if b.data.horizontal:
                horizontal_supporters.append((b, br, overlap))
            else:
                vertical_supporters.append((b, br, overlap))
    
    if horizontal_supporters:
        total_h = sum(ov for _,_,ov in horizontal_supporters)
        if total_h >= 80: 
            return True
    
    if not vertical_supporters:
        return False
    total = sum(ov for _,_,ov in vertical_supporters)
    cnt = len(vertical_supporters)
    if cnt >= 3:
        if cnt >= 4:
            return True
        return total >= 56
    if cnt == 2:
        b1 = vertical_supporters[0][1]
        b2 = vertical_supporters[1][1]
        dist = abs(b1.x - b2.x)
        if dist <= 35: 
            return False
        if 50 <= dist <= 90: 
            return True
    return False

def has_support_physics(rect, shelf_idx, exclude=None):
    if rect.width == 112:
        return has_support_horizontal(rect, shelf_idx, exclude)
    else:
        return has_support_vertical(rect, shelf_idx, exclude) or (shelf_idx is not None and abs(rect.bottom - shelf_system.police_rects[shelf_idx].bottom) <= 4)

def trigger_fall_check():
    changed = True
    while changed:
        changed = False
        for shelf_idx, pr in enumerate(shelf_system.police_rects):
            books_on_shelf = [b for b in placed_books if getattr(b, 'shelf_id', -1) == shelf_idx and not getattr(b, 'is_falling', False) and not getattr(b, 'is_rotating', False)]
            books_on_shelf.sort(key=lambda b: b.get_rect().y, reverse=True)
            for b in books_on_shelf:
                br = b.get_rect()
                if not has_support_physics(br, shelf_idx, exclude=b):
                    if b.data.horizontal:
                        has_h_support = False
                        for ob in placed_books:
                            if ob == b or getattr(ob, 'is_falling', False) or getattr(ob, 'is_rotating', False):
                                continue
                            if getattr(ob, 'shelf_id', -1) != shelf_idx:
                                continue
                            if not ob.data.horizontal:
                                continue
                            obr = ob.get_rect()
                            if abs(obr.y - br.bottom) <= 8:
                                overlap = max(0, min(br.right, obr.right) - max(br.x, obr.x))
                                if overlap >= 80:
                                    has_h_support = True
                                    break
                        if has_h_support:
                            continue
                    
                    b.is_falling = True
                    b.vy = 0
                    b.vx = 0
                    changed = True
                    if b.data.horizontal:
                        verticals_below = []
                        for ob in placed_books:
                            if ob == b:
                                continue
                            if getattr(ob, 'shelf_id', -1) != shelf_idx:
                                continue
                            if ob.data.horizontal:
                                continue
                            obr = ob.get_rect()
                            if abs(obr.y - br.bottom) <= 30:
                                overlap = max(0, min(br.right, obr.right) - max(br.x, obr.x))
                                if overlap > 5:
                                    verticals_below.append(ob)
                        
                        if len(verticals_below) > 0:
                            b.original_horizontal = True
                            b.is_rotating = True
                            b.rotation_progress = 0.0
                            b.pivot_x = br.x
                            b.pivot_y = br.bottom
                        else:
                            b.is_rotating = False
                            b.original_horizontal = False

def find_nearest_vertical_slot(x, shelf_idx, exclude=None):
    pr = shelf_system.police_rects[shelf_idx]
    verticals = [b for b in placed_books if b != exclude and not getattr(b, 'is_falling', False) and not getattr(b, 'is_rotating', False) and getattr(b, 'shelf_id', -1) == shelf_idx and not b.data.horizontal]
    occupied_x = [b.get_rect().x for b in verticals]
    best_x = None
    best_dist = 9999
    for vx in occupied_x:
        for offset in [-28, 28]:
            cand_x = vx + offset
            if cand_x < pr.x or cand_x + 28 > pr.right:
                continue
            free = True
            for ox in occupied_x:
                if abs(ox - cand_x) < 8:
                    free = False
                    break
            if not free:
                continue
            dist = abs(cand_x - x)
            if dist < best_dist:
                best_dist = dist
                best_x = cand_x
    if best_x is None:
        for cand_x in range(int(pr.x), int(pr.right - 28), 28):
            free = True
            for ox in occupied_x:
                if abs(ox - cand_x) < 8:
                    free = False
                    break
            if free:
                dist = abs(cand_x - x)
                if dist < best_dist:
                    best_dist = dist
                    best_x = cand_x
    return best_x

def check_overlap(rect, exclude=None):
    for b in placed_books:
        if b == exclude or getattr(b, 'is_falling', False) or getattr(b, 'is_rotating', False):
            continue
        if b.get_rect().colliderect(rect):
            inter = b.get_rect().clip(rect)
            if inter.width > 6 and inter.height > 6:
                if not (abs(b.get_rect().y - rect.bottom) <= 10 or abs(b.get_rect().bottom - rect.y) <= 10):
                    return True, b
    return False, None

def update_physics(dt):
    trigger_fall_check()
    for b in placed_books:
        if not (getattr(b, 'is_falling', False) or getattr(b, 'is_rotating', False)):
            continue

        if getattr(b, 'is_rotating', False) and getattr(b, 'original_horizontal', False):
            b.rotation_progress += dt * 3.0
            if b.rotation_progress >= 1.0:
                b.rotation_progress = 1.0
                b.is_rotating = False
                b.original_horizontal = False
                shelf_idx = b.shelf_id
                vert_x = find_nearest_vertical_slot(b.data.x, shelf_idx, exclude=b)
                if vert_x is not None:
                    b.data.x = vert_x
                b.data.horizontal = False
                b.rotation = 90
                b.vy = 200
            else:
                b.vy += GRAVITY * dt * 0.5
                b.data.y += b.vy * dt * 0.5
                prog = b.rotation_progress
                b.data.x = b.pivot_x + int(20 * prog)
                continue

        b.vy += GRAVITY * dt
        new_y = b.data.y + b.vy * dt
        test_rect = pygame.Rect(b.data.x, new_y, b.get_rect().width, b.get_rect().height)
        is_overlap, other = check_overlap(test_rect, exclude=b)
        if is_overlap:
            if not b.data.horizontal:
                b.data.y = new_y
                continue
            pr = shelf_system.police_rects[b.shelf_id] if 0 <= b.shelf_id < len(shelf_system.police_rects) else None
            if pr:
                has_verticals = any(not ob.data.horizontal for ob in placed_books if ob != b and getattr(ob, 'shelf_id', -1) == b.shelf_id and not getattr(ob, 'is_falling', False))
                if has_verticals:
                    vert_x = find_nearest_vertical_slot(b.data.x, b.shelf_id, exclude=b)
                    if vert_x is not None:
                        dir_x = vert_x - b.data.x
                        if abs(dir_x) > 2:
                            b.data.x += dir_x * dt * 2
                            b.vy *= 0.8
                        else:
                            b.data.y = new_y
                    else:
                        b.data.y = new_y
                else:
                    b.data.y = new_y
            continue

        b.data.y = new_y
        br = b.get_rect()
        cx = br.centerx
        shelf_idx = b.shelf_id
        if shelf_idx < 0 or shelf_idx >= len(shelf_system.police_rects):
            idx, pr = get_shelf_for_x(cx)
            if pr:
                shelf_idx = idx
                b.shelf_id = idx
            else:
                continue
        pr = shelf_system.police_rects[shelf_idx]
        br = b.get_rect()
        landing = []
        for idx2, pr2 in enumerate(shelf_system.police_rects):
            if pr2.x <= cx <= pr2.right and pr2.bottom >= br.top:
                landing.append((pr2.bottom - br.height, idx2, None, 'floor', pr2.bottom))
        for other in placed_books:
            if other == b or getattr(other, 'is_falling', False) or getattr(other, 'is_rotating', False):
                continue
            obr = other.get_rect()
            if obr.y <= br.y:
                continue
            if br.right <= obr.x + 2 or br.x >= obr.right - 2:
                continue
            overlap = max(0, min(br.right, obr.right) - max(br.x, obr.x))
            if overlap < 5:
                continue
            if br.bottom >= obr.y:
                other_shelf = getattr(other, 'shelf_id', -1)
                test_rect = pygame.Rect(br.x, obr.y - br.height, br.width, br.height)
                if b.data.horizontal:
                    if has_support_horizontal(test_rect, other_shelf, exclude=b):
                        landing.append((obr.y - br.height, other_shelf, other, 'book', obr.y))
                else:
                    if has_support_vertical(test_rect, other_shelf, exclude=b) or other.data.horizontal:
                        landing.append((obr.y - br.height, other_shelf, other, 'book', obr.y))

        landing.sort(key=lambda x: x[0])
        for land_y, s_idx, other, typ, bottom_y in landing:
            if land_y < br.y - 20:
                continue
            if br.bottom >= bottom_y - 12:
                if b.data.horizontal:
                    test_h = pygame.Rect(br.x, land_y, 112, 28)
                    if not has_support_horizontal(test_h, s_idx, exclude=b):
                        verticals_below = []
                        for ob in placed_books:
                            if ob == b:
                                continue
                            if getattr(ob, 'shelf_id', -1) != s_idx:
                                continue
                            if ob.data.horizontal:
                                continue
                            obr = ob.get_rect()
                            if abs(obr.y - test_h.bottom) <= 30:
                                overlap = max(0, min(test_h.right, obr.right) - max(test_h.x, obr.x))
                                if overlap > 5:
                                    verticals_below.append(ob)
                        if len(verticals_below) > 0:
                            vert_x = find_nearest_vertical_slot(br.x, s_idx, exclude=b)
                            if vert_x is not None:
                                b.original_horizontal = True
                                b.is_rotating = True
                                b.rotation_progress = 0.0
                                b.pivot_x = br.x
                                b.pivot_y = br.bottom
                                b.data.x = vert_x
                                break
                b.data.y = land_y
                b.vy = 0
                b.shelf_id = s_idx
                b.is_falling = False
                b.is_rotating = False
                break

        if getattr(b, 'is_falling', False) and b.data.horizontal and not getattr(b, 'is_rotating', False):
            if br.bottom >= pr.bottom - 8:
                test_rect = pygame.Rect(br.x, pr.bottom - 28, 112, 28)
                if not has_support_horizontal(test_rect, shelf_idx, exclude=b):
                    verticals_below = []
                    for ob in placed_books:
                        if ob == b:
                            continue
                        if getattr(ob, 'shelf_id', -1) != shelf_idx:
                            continue
                        if ob.data.horizontal:
                            continue
                        if abs(ob.get_rect().y - test_rect.bottom) <= 30:
                            verticals_below.append(ob)
                    if len(verticals_below) > 0:
                        b.is_rotating = True
                        b.original_horizontal = True
                        b.rotation_progress = 0.0
                        b.pivot_x = br.x
                        b.pivot_y = br.bottom

def get_books_in_police(target):
    return [b for b in placed_books if target.x <= b.get_rect().centerx <= target.right and target.y <= b.get_rect().centery <= target.bottom]

def get_snap_position(mouse_x, mouse_y, w, h):
    target = None
    for pr in shelf_system.police_rects:
        if pr.collidepoint(mouse_x, mouse_y):
            target = pr
            break
    if not target:
        return mouse_x - w // 2, mouse_y - h // 2, False, None
    px1, py1 = target.x, target.y
    px2, py2 = target.right, target.bottom
    base_y = py2 - h
    books_in_police = get_books_in_police(target)
    candidates = []
    for b in books_in_police:
        br = b.get_rect()
        if br.x - 10 <= mouse_x <= br.right + 10 and br.y - 40 <= mouse_y <= br.bottom + 10:
            candidates.append(b)
    candidates.sort(key=lambda b: b.get_rect().y)
    if candidates:
        tb = candidates[0]
        tr = tb.get_rect()
        if not horizontal_mode and tb.data.horizontal:
            slot_w = 28
            rel_x = mouse_x - tr.x
            slot_index = int(rel_x // (tr.width / 4.0))
            slot_index = max(0, min(3, slot_index))
            snap_x = tr.x + slot_index * slot_w
            snap_y = tr.y - h
            for _ in range(4):
                occupied = any(abs(b.get_rect().x - snap_x) <= 1 and abs(b.get_rect().y - snap_y) <= 1 for b in books_in_police if b != tb)
                if not occupied:
                    break
                slot_index = (slot_index + 1) % 4
                snap_x = tr.x + slot_index * slot_w
            return snap_x, snap_y, True, target
        else:
            if horizontal_mode:
                stack_y = tr.y - h
                if not tb.data.horizontal:
                    nearby_vertical = []
                    for b in books_in_police:
                        if b.data.horizontal:
                            continue
                        br = b.get_rect()
                        if abs(br.y - tr.y) > 2:
                            continue
                        if abs(br.centerx - mouse_x) < 200:
                            nearby_vertical.append(b)
                    nearby_vertical.sort(key=lambda b: b.get_rect().x)
                    possible = []
                    for i in range(len(nearby_vertical) - 3):
                        four = nearby_vertical[i:i + 4]
                        if four[3].get_rect().x - four[0].get_rect().x == 84:
                            possible.append(four[0].get_rect().x)
                    for i in range(len(nearby_vertical) - 2):
                        three = nearby_vertical[i:i + 3]
                        if three[2].get_rect().x - three[0].get_rect().x != 56:
                            continue
                        min_x = three[0].get_rect().x
                        possible.append(min_x)
                        possible.append(min_x - 14)
                        possible.append(min_x - 28)
                    if possible:
                        best = min(possible, key=lambda sx: abs((sx + w // 2) - mouse_x))
                        snap_x = max(px1, min(px2 - w, best))
                        snap_y = stack_y
                        return snap_x, snap_y, True, target
                same_level = [b for b in books_in_police if b.data.horizontal and abs(b.get_rect().y - stack_y) <= 2]
                snap_x = tr.x
                snap_y = stack_y
                if any(abs(b.get_rect().x - snap_x) <= 1 for b in same_level):
                    for b in same_level:
                        br = b.get_rect()
                        tx = br.right
                        if not any(abs(ob.get_rect().x - tx) <= 1 for ob in same_level) and px1 <= tx <= px2 - w:
                            snap_x = tx
                            break
                        tx = br.x - w
                        if not any(abs(ob.get_rect().x - tx) <= 1 for ob in same_level) and px1 <= tx <= px2 - w:
                            snap_x = tx
                            break
                    else:
                        snap_x = mouse_x - w // 2
                        for b in same_level:
                            br = b.get_rect()
                            if abs(snap_x - br.right) < 18:
                                snap_x = br.right
                            if abs(snap_x + w - br.x) < 18:
                                snap_x = br.x - w
                snap_x = max(px1, min(px2 - w, snap_x))
                if snap_y < py1:
                    return max(px1, min(px2 - w, mouse_x - w // 2)), base_y, True, target
                return snap_x, snap_y, True, target
            else:
                half = (tr.width + w) // 2
                sign = 1 if mouse_x >= tr.centerx else -1
                snap_x = tr.centerx + sign * half - w // 2
                snap_y = tr.y
                snap_x = max(px1, min(px2 - w, snap_x))
                return snap_x, snap_y, True, target
    snap_y = base_y
    snap_x = mouse_x - w // 2
    for b in books_in_police:
        br = b.get_rect()
        if abs(br.y - snap_y) > 2:
            continue
        if not horizontal_mode and b.data.horizontal:
            continue
        if horizontal_mode and not b.data.horizontal:
            continue
        if abs(snap_x - br.right) < 20:
            snap_x = br.right
        if abs(snap_x + w - br.x) < 20:
            snap_x = br.x - w
    snap_x = max(px1, min(px2 - w, snap_x))
    return snap_x, snap_y, True, target

def has_support(rect, target):
    if abs(rect.bottom - target.bottom) <= 1:
        return True
    supporters = []
    vertical_supporters = []
    horizontal_supporters = []
    for b in placed_books:
        br = b.get_rect()
        if abs(br.y - rect.bottom) <= 1 or abs(br.y + br.height - rect.y) <= 1:
            overlap = max(0, min(rect.right, br.right) - max(rect.x, br.x))
            if overlap > 0:
                supporters.append((b, overlap))
                if b.data.horizontal:
                    horizontal_supporters.append((b, overlap))
                else:
                    vertical_supporters.append((b, overlap))
    if not supporters:
        return False
    total_overlap = sum(ov for _, ov in supporters)
    count_supporters = len(supporters)
    if rect.width == 112:
        if horizontal_supporters and sum(ov for _,ov in horizontal_supporters) >= 80:
            return True
        if len(vertical_supporters) >= 3:
            return total_overlap >= 56 or count_supporters >= 3
        if len(vertical_supporters) == 2:
            verts = []
            for b in placed_books:
                if b.data.horizontal:
                    continue
                br = b.get_rect()
                if abs(br.y - rect.bottom) <= 10 or abs(br.y + br.height - rect.y) <= 10:
                    if max(0, min(rect.right, br.right) - max(rect.x, br.x)) > 0:
                        verts.append(br)
            if len(verts) == 2:
                dist = abs(verts[0].x - verts[1].x)
                if dist <= 35: 
                    return False
                if 50 <= dist <= 90:
                    return True
        return False
    else:
        return total_overlap >= 10

def check_valid(rect, target):
    if target is None:
        return False
    if not (target.x - 2 <= rect.x and rect.right <= target.right + 2 and target.y - 2 <= rect.y and rect.bottom <= target.bottom + 2):
        return False
    for b in placed_books:
        br = b.get_rect()
        if rect.colliderect(br):
            if abs(rect.x - br.x) <= 1 and abs(rect.bottom - br.y) <= 1:
                continue
            inter_x = max(0, min(rect.right, br.right) - max(rect.x, br.x))
            inter_y = max(0, min(rect.bottom, br.bottom) - max(rect.y, br.y))
            if inter_x < 16 and inter_y < 5:
                continue
            if inter_x * inter_y < 30:
                continue
            return False
    if not has_support(rect, target):
        return False
    return True

running = True
while running:
    dt = clock.tick(60) / 1000.0
    mouse_x, mouse_y = pygame.mouse.get_pos()
    update_physics(dt)
    drag_book.data.horizontal = horizontal_mode
    if horizontal_mode:
        rw = 112
        rh = 28
    else:
        rw = 28
        rh = 112
    snap_x, snap_y, has_police, target_police = get_snap_position(mouse_x, mouse_y, rw, rh)
    phantom.data.x = snap_x
    phantom.data.y = snap_y
    phantom.data.horizontal = horizontal_mode
    drag_book.data.x = snap_x
    drag_book.data.y = snap_y
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_q:
                horizontal_mode = True
            if event.key == pygame.K_e:
                horizontal_mode = False
            if event.key == pygame.K_s:
                session = get_session(db_path)
                session.query(BookModel).filter_by(project_name="mvp").delete()
                for b in placed_books:
                    if getattr(b, 'is_falling', False) or getattr(b, 'is_rotating', False):
                        continue
                    r = b.get_rect()
                    session.add(BookModel(project_name="mvp", title=b.data.title, x=r.x, y=r.y, width=r.width, height=r.height, rotation=0, horizontal=b.data.horizontal))
                session.commit()
                session.close()
            if event.key == pygame.K_l:
                session = get_session(db_path)
                rows = session.query(BookModel).filter_by(project_name="mvp").all()
                placed_books.clear()
                for row in rows:
                    d = BookData(title=row.title, width=row.width, height=row.height, x=row.x, y=row.y, rotation=0, horizontal=row.horizontal)
                    nb = Book(d)
                    for idx, pr in enumerate(shelf_system.police_rects):
                        if pr.x <= d.x <= pr.right:
                            nb.shelf_id = idx
                            break
                    placed_books.append(nb)
                session.close()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                rect = phantom.get_rect()
                if has_police and check_valid(rect, target_police):
                    new_data = BookData(title=drag_book.data.title, width=28, height=112, color=drag_book.data.color, x=rect.x, y=rect.y, rotation=0, horizontal=horizontal_mode)
                    nb = Book(new_data)
                    nb.shelf_id = shelf_system.police_rects.index(target_police) if target_police in shelf_system.police_rects else 0
                    placed_books.append(nb)
                    current_data.color = (random.randint(180, 230), random.randint(160, 210), random.randint(120, 180))
            elif event.button == 3:
                hit_book = None
                for b in reversed(placed_books):
                    if b.get_rect().collidepoint(event.pos):
                        hit_book = b
                        break
                if not hit_book:
                    for b in placed_books:
                        br = b.get_rect()
                        if br.x - 5 <= event.pos[0] <= br.right + 5 and br.y - 5 <= event.pos[1] <= br.bottom + 5:
                            if hit_book is None or br.y < hit_book.get_rect().y:
                                hit_book = b
                if hit_book:
                    placed_books.remove(hit_book)
                    current_data.color = hit_book.data.color
                    horizontal_mode = hit_book.data.horizontal
                    trigger_fall_check()
    screen.fill((235, 230, 220))
    shelf_system.draw(screen)
    for b in placed_books:
        b.draw(screen)
    valid = has_police and check_valid(phantom.get_rect(), target_police)
    phantom.draw(screen, is_valid=valid)
    screen.blit(font.render(f"[Q]H [E]V | Книг: {len(placed_books)} | Оранж->Синяя с переворотом | Падают: {len([b for b in placed_books if b.is_falling or b.is_rotating])}", True, (60,50,30)), (10, H-50))
    screen.blit(font.render(f"Не застревает в текстуре - скользит к свободному слоту | ПКМ забрать", True, (60,50,30)), (10, H-30))
    pygame.display.flip()
pygame.quit()
sys.exit()
