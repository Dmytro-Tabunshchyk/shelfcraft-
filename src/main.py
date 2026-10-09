import pygame, pathlib, sys, random
from book_physics import Book, PhantomBook, BookData
from shelf import ShelfSystem
from db import get_session, BookModel

pygame.init()
W, H = 1280, 720
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("ShelfCraft Physics")
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
    cnt = len(vertical_supporters)
    if cnt >= 3:
        if cnt >= 4:
            return True
        total = sum(ov for _,_,ov in vertical_supporters)
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
                        b.is_rotating = True
                        b.rotation_progress = 0.0
                        b.original_horizontal = True
                        b.will_be_vertical = True

def update_physics(dt):
    trigger_fall_check()
    for b in placed_books:
        if getattr(b, 'is_rotating', False):
            b.rotation_progress += dt * 3.0
            if b.rotation_progress >= 1.0:
                b.rotation_progress = 1.0
                b.is_rotating = False
                b.data.horizontal = False
                b.original_horizontal = False
            continue
        if not getattr(b, 'is_falling', False):
            continue
        b.vy += GRAVITY * dt
        b.data.y += b.vy * dt
        br = b.get_rect()
        cx = br.centerx
        landing_candidates = []
        for idx, pr in enumerate(shelf_system.police_rects):
            if pr.x <= cx <= pr.right and pr.bottom >= br.top:
                landing_y = pr.bottom - br.height
                if landing_y >= br.y - 5:
                    landing_candidates.append((landing_y, idx, None, 'floor'))
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
                if has_support_physics(test_rect, other_shelf, exclude=b):
                    landing_candidates.append((obr.y - br.height, other_shelf, other, 'book'))
        landing_candidates.sort(key=lambda x: x[0])
        for land_y, shelf_idx, other, typ in landing_candidates:
            if land_y < br.y - 10:
                continue
            if br.bottom >= (other.get_rect().y if typ == 'book' else shelf_system.police_rects[shelf_idx].bottom) - 5:
                b.data.y = land_y
                b.vy = 0
                b.shelf_id = shelf_idx
                b.is_falling = False
                break
        if getattr(b, 'is_falling', False) and br.bottom > 2000:
            idx, pr = get_shelf_for_x(cx)
            if pr:
                b.data.y = pr.bottom - br.height
                b.shelf_id = idx
                b.is_falling = False
                b.vy = 0

def get_books_in_police(target):
    return [b for b in placed_books if target.x <= b.get_rect().centerx <= target.right and target.y <= b.get_rect().centery <= target.bottom]

def get_snap_position(mouse_x, mouse_y, w, h):
    target = None
    for pr in shelf_system.police_rects:
        if pr.x <= mouse_x <= pr.right and pr.y <= mouse_y <= pr.bottom:
            target = pr
            break
    if target is None:
        closest = None
        min_dist = float('inf')
        for pr in shelf_system.police_rects:
            dist = abs(mouse_y - (pr.y + pr.bottom)//2)
            if dist < min_dist:
                min_dist = dist
                closest = pr
        if closest:
            target = closest
    if target is None:
        return mouse_x, mouse_y, False, None
    px1 = target.x
    px2 = target.right
    snap_x = mouse_x - w//2
    snap_y = target.bottom - h
    books_on_target = get_books_in_police(target)
    if not horizontal_mode:
        books_on_target = [b for b in books_on_target if not b.data.horizontal]
        books_on_target.sort(key=lambda b: b.get_rect().x)
        for b in books_on_target:
            br = b.get_rect()
            if abs(snap_x - br.x) < 20:
                snap_x = br.x
            if abs(snap_x + w - br.right) < 20:
                snap_x = br.right
    else:
        books_on_target = [b for b in books_on_target if b.data.horizontal]
        books_on_target.sort(key=lambda b: b.get_rect().y)
        for b in books_on_target:
            br = b.get_rect()
            if abs(snap_y - br.y) < 20:
                snap_y = br.y
            if abs(snap_y + h - br.bottom) < 20:
                snap_y = br.bottom - h
    for b in placed_books:
        if getattr(b, 'shelf_id', -1) != (shelf_system.police_rects.index(target) if target in shelf_system.police_rects else -1):
            continue
        if not horizontal_mode and b.data.horizontal:
            continue
        if horizontal_mode and not b.data.horizontal:
            continue
        br = b.get_rect()
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
    for b in placed_books:
        br = b.get_rect()
        if abs(br.y + br.height - rect.y) <= 1 or abs(br.y - rect.bottom) <= 1 or abs(br.bottom - rect.y) <= 1:
            overlap = max(0, min(rect.right, br.right) - max(rect.x, br.x))
            if overlap > 0:
                supporters.append((b, overlap))
    if not supporters:
        return False
    total_overlap = sum(ov for _, ov in supporters)
    count_supporters = len(supporters)
    vertical_supporters = [b for b, _ in supporters if not b.data.horizontal]
    horizontal_supporters = [b for b, _ in supporters if b.data.horizontal]
    if rect.width == 112:
        if horizontal_supporters:
            total_h = sum(ov for b, ov in supporters if b.data.horizontal)
            if total_h >= 80:
                return True
        if len(vertical_supporters) >= 3:
            return True
        if len(vertical_supporters) == 2:
            verts = []
            for b, _ in supporters:
                if b.data.horizontal:
                    continue
                verts.append(b.get_rect())
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
    rw = 112 if horizontal_mode else 28
    rh = 28 if horizontal_mode else 112
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
    screen.blit(font.render(f"[Q]H [E]V | Books: {len(placed_books)} | Falling: {len([b for b in placed_books if b.is_falling or b.is_rotating])}", True, (60,50,30)), (10, H-30))
    pygame.display.flip()

pygame.quit()
sys.exit()
