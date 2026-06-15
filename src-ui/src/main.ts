import {
  importProvidersFrom,
  inject,
  provideAppInitializer,
  provideZoneChangeDetection,
} from '@angular/core'

import { DragDropModule } from '@angular/cdk/drag-drop'
import { DatePipe, registerLocaleData } from '@angular/common'
import {
  provideHttpClient,
  withFetch,
  withInterceptors,
  withInterceptorsFromDi,
} from '@angular/common/http'
import { FormsModule, ReactiveFormsModule } from '@angular/forms'
import { BrowserModule, bootstrapApplication } from '@angular/platform-browser'
import {
  NgbDateAdapter,
  NgbDateParserFormatter,
  NgbModule,
} from '@ng-bootstrap/ng-bootstrap'
import { NgSelectModule } from '@ng-select/ng-select'
import {
  Archive,
  ArrowDown,
  ArrowDownAZ,
  ArrowLeft,
  ArrowRight,
  ArrowUpAZ,
  ArrowUpDown,
  ArrowUpRight,
  Asterisk,
  AtSign,
  Bell,
  Bookmark,
  Braces,
  Calendar,
  CalendarDays,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  ChevronsLeft,
  ChevronsRight,
  Circle,
  CircleAlert,
  CircleCheck,
  CircleHelp,
  CircleMinus,
  CirclePlus,
  CircleSlash,
  CircleUser,
  CircleX,
  Clipboard,
  ClipboardCheck,
  ClipboardList,
  Dice5,
  Download,
  Ellipsis,
  EllipsisVertical,
  ExternalLink,
  Eye,
  File,
  FileCheck,
  FileDiff,
  FileLock,
  FilePlus,
  FileText,
  Files,
  Filter,
  Folder,
  Funnel,
  GripVertical,
  Hash,
  Heading,
  History,
  House,
  IndentIncrease,
  Info,
  Layers,
  LayoutGrid,
  Library,
  Link,
  List,
  ListChecks,
  ListTodo,
  ListTree,
  LockOpen,
  LogOut,
  LucideAngularModule,
  X as LucideX,
  Mail,
  MessageSquareText,
  Minus,
  Pencil,
  Plane,
  Play,
  Plus,
  Printer,
  RotateCcw,
  RotateCw,
  ScanBarcode,
  Scissors,
  ScrollText,
  Search,
  Send,
  Server,
  Settings,
  SlidersVertical,
  Sparkles,
  Tags,
  Text,
  Trash2,
  TriangleAlert,
  Upload,
  User,
  UserLock,
  Users,
  Workflow,
} from 'lucide-angular'
import {
  NgxBootstrapIconsModule,
  airplane,
  archive,
  arrowClockwise,
  arrowCounterclockwise,
  arrowDown,
  arrowDownUp,
  arrowLeft,
  arrowRepeat,
  arrowRight,
  arrowRightShort,
  arrowUpRight,
  arrowsFullscreen,
  asterisk,
  bell,
  bodyText,
  boxArrowUp,
  boxArrowUpRight,
  boxes,
  braces,
  calendar,
  calendarEvent,
  calendarEventFill,
  cardChecklist,
  cardHeading,
  caretDown,
  caretUp,
  chatLeftText,
  chatSquareDots,
  check,
  check2All,
  checkAll,
  checkCircle,
  checkCircleFill,
  checkLg,
  chevronDoubleLeft,
  chevronDoubleRight,
  chevronDown,
  chevronRight,
  circle,
  clipboard,
  clipboardCheck,
  clipboardCheckFill,
  clipboardFill,
  clockHistory,
  dash,
  dashCircle,
  diagram3,
  dice5,
  doorOpen,
  download,
  envelope,
  envelopeAt,
  envelopeAtFill,
  exclamationCircleFill,
  exclamationTriangle,
  exclamationTriangleFill,
  eye,
  fileEarmark,
  fileEarmarkCheck,
  fileEarmarkDiff,
  fileEarmarkFill,
  fileEarmarkLock,
  fileEarmarkMinus,
  fileEarmarkPlus,
  fileEarmarkRichtext,
  fileText,
  files,
  filter,
  folder,
  folderFill,
  fullscreen,
  funnel,
  gear,
  google,
  grid,
  gripVertical,
  hash,
  hddStack,
  house,
  infoCircle,
  journals,
  link,
  listNested,
  listTask,
  listUl,
  microsoft,
  nodePlus,
  pencil,
  people,
  peopleFill,
  person,
  personCircle,
  personFill,
  personFillLock,
  personLock,
  personSquare,
  playFill,
  plus,
  plusCircle,
  printer,
  questionCircle,
  scissors,
  search,
  send,
  slashCircle,
  sliders2Vertical,
  sortAlphaDown,
  sortAlphaUpAlt,
  stack,
  stars,
  tag,
  tagFill,
  tags,
  textIndentLeft,
  textLeft,
  threeDots,
  threeDotsVertical,
  trash,
  uiRadios,
  unlock,
  upcScan,
  windowStack,
  x,
  xCircle,
  xLg,
} from 'ngx-bootstrap-icons'
import { ColorSliderModule } from 'ngx-color/slider'
import { CookieService } from 'ngx-cookie-service'
import { MARKED_OPTIONS, MarkdownModule } from 'ngx-markdown'
import { AppRoutingModule } from './app/app-routing.module'
import { AppComponent } from './app/app.component'
import { DirtyDocGuard } from './app/guards/dirty-doc.guard'
import { DirtySavedViewGuard } from './app/guards/dirty-saved-view.guard'
import { PermissionsGuard } from './app/guards/permissions.guard'
import { withApiVersionInterceptor } from './app/interceptors/api-version.interceptor'
import { withAuthExpiryInterceptor } from './app/interceptors/auth-expiry.interceptor'
import { withCsrfInterceptor } from './app/interceptors/csrf.interceptor'
import { DocumentTitlePipe } from './app/pipes/document-title.pipe'
import { FilterPipe } from './app/pipes/filter.pipe'
import { UsernamePipe } from './app/pipes/username.pipe'
import { SettingsService } from './app/services/settings.service'
import { LocalizedDateParserFormatter } from './app/utils/ngb-date-parser-formatter'
import { ISODateAdapter } from './app/utils/ngb-iso-date-adapter'

import localeAf from '@angular/common/locales/af'
import localeAr from '@angular/common/locales/ar'
import localeBe from '@angular/common/locales/be'
import localeBg from '@angular/common/locales/bg'
import localeCa from '@angular/common/locales/ca'
import localeCs from '@angular/common/locales/cs'
import localeDa from '@angular/common/locales/da'
import localeDe from '@angular/common/locales/de'
import localeEl from '@angular/common/locales/el'
import localeEnGb from '@angular/common/locales/en-GB'
import localeEs from '@angular/common/locales/es'
import localeFa from '@angular/common/locales/fa'
import localeFi from '@angular/common/locales/fi'
import localeFr from '@angular/common/locales/fr'
import localeHu from '@angular/common/locales/hu'
import localeId from '@angular/common/locales/id'
import localeIt from '@angular/common/locales/it'
import localeJa from '@angular/common/locales/ja'
import localeKo from '@angular/common/locales/ko'
import localeLb from '@angular/common/locales/lb'
import localeNl from '@angular/common/locales/nl'
import localeNo from '@angular/common/locales/no'
import localePl from '@angular/common/locales/pl'
import localePt from '@angular/common/locales/pt'
import localeRo from '@angular/common/locales/ro'
import localeRu from '@angular/common/locales/ru'
import localeSk from '@angular/common/locales/sk'
import localeSl from '@angular/common/locales/sl'
import localeSr from '@angular/common/locales/sr'
import localeSv from '@angular/common/locales/sv'
import localeTr from '@angular/common/locales/tr'
import localeUk from '@angular/common/locales/uk'
import localeVi from '@angular/common/locales/vi'
import localeZh from '@angular/common/locales/zh'
import localeZhHant from '@angular/common/locales/zh-Hant'
import { provideUiTour } from 'ngx-ui-tour-ng-bootstrap'
import { CorrespondentNamePipe } from './app/pipes/correspondent-name.pipe'
import { DocumentTypeNamePipe } from './app/pipes/document-type-name.pipe'
import { StoragePathNamePipe } from './app/pipes/storage-path-name.pipe'
import { MarkdownConfigService } from './app/services/markdown-config.service'

registerLocaleData(localeAf)
registerLocaleData(localeAr)
registerLocaleData(localeBe)
registerLocaleData(localeBg)
registerLocaleData(localeCa)
registerLocaleData(localeCs)
registerLocaleData(localeDa)
registerLocaleData(localeDe)
registerLocaleData(localeEl)
registerLocaleData(localeEnGb)
registerLocaleData(localeEs)
registerLocaleData(localeFa)
registerLocaleData(localeFi)
registerLocaleData(localeFr)
registerLocaleData(localeHu)
registerLocaleData(localeId)
registerLocaleData(localeIt)
registerLocaleData(localeJa)
registerLocaleData(localeKo)
registerLocaleData(localeLb)
registerLocaleData(localeNl)
registerLocaleData(localeNo)
registerLocaleData(localePl)
registerLocaleData(localePt, 'pt-BR')
registerLocaleData(localePt, 'pt-PT')
registerLocaleData(localeRo)
registerLocaleData(localeRu)
registerLocaleData(localeSk)
registerLocaleData(localeSl)
registerLocaleData(localeSr)
registerLocaleData(localeSv)
registerLocaleData(localeTr)
registerLocaleData(localeVi)
registerLocaleData(localeUk)
registerLocaleData(localeZh)
registerLocaleData(localeZhHant)

function initializeApp() {
  const settings = inject(SettingsService)
  return settings.initializeSettings()
}

const icons = {
  airplane,
  archive,
  arrowClockwise,
  arrowCounterclockwise,
  arrowDown,
  arrowDownUp,
  arrowLeft,
  arrowRepeat,
  arrowRight,
  arrowRightShort,
  arrowUpRight,
  asterisk,
  bell,
  braces,
  bodyText,
  boxArrowUp,
  boxArrowUpRight,
  boxes,
  calendar,
  calendarEvent,
  calendarEventFill,
  cardChecklist,
  cardHeading,
  caretDown,
  caretUp,
  chatLeftText,
  chatSquareDots,
  check,
  check2All,
  checkAll,
  checkCircle,
  checkCircleFill,
  checkLg,
  chevronDoubleLeft,
  chevronDoubleRight,
  chevronDown,
  chevronRight,
  circle,
  clipboard,
  clipboardCheck,
  clipboardCheckFill,
  clipboardFill,
  clockHistory,
  dash,
  dashCircle,
  diagram3,
  dice5,
  doorOpen,
  download,
  envelope,
  envelopeAt,
  envelopeAtFill,
  exclamationCircleFill,
  exclamationTriangle,
  exclamationTriangleFill,
  eye,
  fileEarmark,
  fileEarmarkCheck,
  fileEarmarkDiff,
  fileEarmarkFill,
  fileEarmarkLock,
  fileEarmarkMinus,
  fileEarmarkPlus,
  fileEarmarkRichtext,
  files,
  fileText,
  filter,
  folder,
  folderFill,
  fullscreen,
  arrowsFullscreen,
  funnel,
  gear,
  google,
  grid,
  gripVertical,
  hash,
  hddStack,
  house,
  infoCircle,
  journals,
  link,
  listNested,
  listTask,
  listUl,
  microsoft,
  nodePlus,
  pencil,
  people,
  peopleFill,
  person,
  personCircle,
  personFill,
  personFillLock,
  personLock,
  personSquare,
  playFill,
  plus,
  plusCircle,
  printer,
  questionCircle,
  scissors,
  search,
  send,
  slashCircle,
  sliders2Vertical,
  sortAlphaDown,
  sortAlphaUpAlt,
  stack,
  stars,
  tagFill,
  tag,
  tags,
  textIndentLeft,
  textLeft,
  threeDots,
  threeDotsVertical,
  trash,
  uiRadios,
  unlock,
  upcScan,
  windowStack,
  x,
  xCircle,
  xLg,
}

bootstrapApplication(AppComponent, {
  providers: [
    provideZoneChangeDetection(),
    importProvidersFrom(
      BrowserModule,
      AppRoutingModule,
      NgbModule,
      FormsModule,
      ReactiveFormsModule,
      NgSelectModule,
      ColorSliderModule,
      DragDropModule,
      NgxBootstrapIconsModule.pick(icons),
      // Lucide is the app's icon set. Templates keep their original (Bootstrap)
      // icon names; each is aliased here to the matching Lucide glyph, so no
      // template name changes (or dynamic-binding changes) were needed. Brand
      // logos (google/microsoft) have no Lucide equivalent and stay on
      // ngx-bootstrap-icons above.
      LucideAngularModule.pick({
        // chrome / navigation
        House,
        Files,
        FileText,
        Stack: Layers,
        Tags,
        TagFill: Tags,
        Person: User,
        PersonFill: User,
        Hash,
        Folder,
        FolderFill: Folder,
        UiRadios: ListChecks,
        WindowStack: Bookmark,
        Boxes: Workflow,
        Envelope: Mail,
        Trash: Trash2,
        Gear: Settings,
        Sliders2Vertical: SlidersVertical,
        People: Users,
        ListTask: ListTodo,
        TextLeft: ScrollText,
        QuestionCircle: CircleHelp,
        InfoCircle: Info,
        ChevronDoubleRight: ChevronsRight,
        ChevronDoubleLeft: ChevronsLeft,
        GripVertical,
        DoorOpen: LogOut,
        PersonCircle: CircleUser,
        Funnel,
        X: LucideX,
        // actions / status
        ExclamationTriangleFill: TriangleAlert,
        ExclamationTriangle: TriangleAlert,
        ExclamationCircleFill: CircleAlert,
        Check,
        CheckLg: Check,
        Check2All: CheckCheck,
        CheckAll: CheckCheck,
        CheckCircle: CircleCheck,
        CheckCircleFill: CircleCheck,
        PlusCircle: CirclePlus,
        Plus,
        NodePlus: CirclePlus,
        Pencil,
        Eye,
        ThreeDotsVertical: EllipsisVertical,
        ThreeDots: Ellipsis,
        Filter,
        SlashCircle: CircleSlash,
        ArrowCounterclockwise: RotateCcw,
        ArrowClockwise: RotateCw,
        Download,
        Upload,
        BoxArrowUp: Upload,
        BoxArrowUpRight: ExternalLink,
        Link,
        Send,
        Airplane: Plane,
        Search,
        PlayFill: Play,
        Scissors,
        Printer,
        Archive,
        Dash: Minus,
        DashCircle: CircleMinus,
        Asterisk,
        Stars: Sparkles,
        Braces,
        UpcScan: ScanBarcode,
        // files / clipboard
        FileEarmark: File,
        FileEarmarkFill: File,
        FileEarmarkRichtext: FileText,
        FileEarmarkCheck: FileCheck,
        FileEarmarkPlus: FilePlus,
        FileEarmarkLock: FileLock,
        FileEarmarkDiff: FileDiff,
        Clipboard,
        ClipboardFill: Clipboard,
        ClipboardCheck,
        ClipboardCheckFill: ClipboardCheck,
        CardChecklist: ClipboardList,
        CardHeading: Heading,
        BodyText: Text,
        Journals: Library,
        ListUl: List,
        ListNested: ListTree,
        // people / permissions
        PersonLock: UserLock,
        PersonFillLock: UserLock,
        PeopleFill: Users,
        Unlock: LockOpen,
        // calendar / dates / misc
        Calendar,
        CalendarEvent: CalendarDays,
        CalendarEventFill: Calendar,
        ClockHistory: History,
        Bell,
        ChatLeftText: MessageSquareText,
        EnvelopeAtFill: AtSign,
        Diagram3: Workflow,
        HddStack: Server,
        Grid: LayoutGrid,
        Dice5,
        Circle,
        // arrows / carets / chevrons / sorting
        ArrowRight,
        ArrowRightShort: ArrowRight,
        ArrowLeft,
        ArrowDown,
        ArrowUpRight,
        ArrowDownUp: ArrowUpDown,
        ChevronRight,
        CaretUp: ChevronUp,
        CaretDown: ChevronDown,
        SortAlphaDown: ArrowDownAZ,
        SortAlphaUpAlt: ArrowUpAZ,
        XCircle: CircleX,
        XLg: LucideX,
        TextIndentLeft: IndentIncrease,
      }),
      MarkdownModule.forRoot({
        markedOptions: {
          provide: MARKED_OPTIONS,
          useFactory: (markdownConfigService: MarkdownConfigService) =>
            markdownConfigService.createMarkedOptions(),
          deps: [MarkdownConfigService],
        },
      })
    ),
    provideAppInitializer(initializeApp),
    DatePipe,
    CookieService,
    FilterPipe,
    DocumentTitlePipe,
    { provide: NgbDateAdapter, useClass: ISODateAdapter },
    { provide: NgbDateParserFormatter, useClass: LocalizedDateParserFormatter },
    PermissionsGuard,
    DirtyDocGuard,
    DirtySavedViewGuard,
    UsernamePipe,
    CorrespondentNamePipe,
    DocumentTypeNamePipe,
    StoragePathNamePipe,
    provideHttpClient(
      withInterceptorsFromDi(),
      withInterceptors([
        withCsrfInterceptor,
        withApiVersionInterceptor,
        withAuthExpiryInterceptor,
      ]),
      withFetch()
    ),
    provideUiTour({
      enableBackdrop: true,
      backdropConfig: {
        offset: 10,
      },
      prevBtnTitle: $localize`Prev`,
      nextBtnTitle: $localize`Next`,
      endBtnTitle: $localize`End`,
      isOptional: true,
      useLegacyTitle: true,
    }),
  ],
}).catch((err) => console.error(err))
